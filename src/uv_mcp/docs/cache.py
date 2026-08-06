import asyncio
import json
import logging
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import httpx

from uv_mcp.docs.constants import (
    DOCS_URLS,
    DOCUMENTATION_SECTIONS,
    HTTP_TIMEOUT,
    PYPI_UV_URL,
    VERSION_FILE,
    Section,
)
from uv_mcp.docs.parsing import SECTION_SPECS, SectionPayload, parse_section
from uv_mcp.docs.queries import command_docs, section_overview, subsection_docs
from uv_mcp.docs.search import search_sections

logger = logging.getLogger(__name__)


async def _read_json(path: Path) -> dict[str, Any]:
    """Read a JSON file, returning an empty dict on failure."""
    try:
        return json.loads(await asyncio.to_thread(path.read_text, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


async def _write_json(path: Path, data: Mapping[str, Any]) -> None:
    """Write a JSON file atomically via a temporary file."""

    def write() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(temporary, path)

    await asyncio.to_thread(write)


async def _fetch_text(url: str) -> str:
    """Fetch a URL and return the response body as text."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=HTTP_TIMEOUT) as client:
        response = await client.get(url)
        response.raise_for_status()

        return response.text


class CacheManager:
    """Fetch, store, and query the cached UV documentation."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize the cache manager."""
        if cache_dir is None:
            cache_root = Path(os.getenv("XDG_CACHE_HOME", str(Path.home() / ".cache")))
            cache_dir = cache_root / "uv-mcp" / "docs"
        self.cache_dir = cache_dir
        self.version_file = cache_dir / VERSION_FILE

    async def initialize(self) -> None:
        """Initialize the cache, fetching documentation when it is missing."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if self.version_file.exists():
            logger.info("Documentation cache found at %s", self.cache_dir)

            return

        try:
            await self.update_version(await self.fetch_current_version())
            for section in DOCUMENTATION_SECTIONS:
                await self.update_section(section, await self.fetch_section(section))
        except Exception:
            logger.exception("Failed to initialize documentation cache")
            if not self.version_file.exists():
                await self.update_version({"version": "unknown"})

    async def get_cached_version(self) -> dict[str, str]:
        """Get the cached UV version information."""
        return await _read_json(self.version_file)

    async def update_version(self, version_info: dict[str, str]) -> None:
        """Update the cached version information."""
        await _write_json(self.version_file, version_info)

    def get_section_cache_path(self, section: str) -> Path:
        """Get the cache file path for a documentation section."""
        return self.cache_dir / f"{section}.json"

    async def get_cached_section(self, section: str) -> dict[str, Any]:
        """Get cached content for a documentation section."""
        return await _read_json(self.get_section_cache_path(section))

    async def update_section(
        self, section: str, content: dict[str, Any] | SectionPayload
    ) -> None:
        """Update the cache for a documentation section."""
        await _write_json(self.get_section_cache_path(section), content)

    async def clear_cache(self) -> None:
        """Clear all cached documentation files."""
        files = list(self.cache_dir.glob("*.json"))
        if files:
            await asyncio.gather(*(asyncio.to_thread(file.unlink) for file in files))

    async def is_cache_valid(self) -> bool:
        """Check whether the cache matches the current UV version."""
        try:
            current_version = await self.fetch_current_version()
            cached_version = await self.get_cached_version()
        except Exception:
            logger.exception("Failed to check cache validity")

            return False

        return cached_version.get("version") == current_version.get("version")

    async def fetch_current_version(self) -> dict[str, str]:
        """Fetch the current UV version from PyPI."""
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=HTTP_TIMEOUT
        ) as client:
            response = await client.get(PYPI_UV_URL)
            try:
                response.raise_for_status()
                info = response.json()["info"]
            except (httpx.HTTPError, KeyError, ValueError):
                return {"version": "unknown"}

            return {"version": info["version"]}

    async def fetch_section(self, section: str) -> SectionPayload:
        """Fetch and parse a documentation section from the UV docs website."""
        name = cast(Section, section)
        html = await _fetch_text(DOCS_URLS[name])

        return parse_section(html, SECTION_SPECS[name])

    async def get_section_overview(self, section: str) -> dict[str, Any]:
        """Return a section's command list, or raise if it is not cached."""
        return section_overview(section, await self.get_cached_section(section))

    async def get_command_docs(self, section: str, command: str) -> dict[str, Any]:
        """Return metadata and subsection links for a command."""
        return command_docs(section, command, await self.get_cached_section(section))

    async def get_subsection_docs(
        self, section: str, command: str, subsection: str
    ) -> dict[str, Any]:
        """Return the detailed content of a command subsection."""
        return subsection_docs(
            section, command, subsection, await self.get_cached_section(section)
        )

    async def search(self, query: str) -> list[dict[str, str]]:
        """Search cached documentation, returning the best matching resources."""
        return await search_sections(self.get_cached_section, query)
