"""UV documentation fetching, parsing, and caching.

Documentation is fetched from the UV docs website, parsed into a
structured JSON shape, and cached on disk (XDG cache directory by
default) so MCP clients can read sections without repeated network
requests.
"""

import asyncio
import json
import logging
import os
import unicodedata
from difflib import get_close_matches
from pathlib import Path
from typing import Any, TypedDict

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DOCUMENTATION_SECTIONS = ("cli", "settings", "resolver")

DOCS_URLS = {
    "cli": "https://docs.astral.sh/uv/reference/cli/",
    "settings": "https://docs.astral.sh/uv/reference/settings/",
    "resolver": "https://docs.astral.sh/uv/reference/resolver-internals/",
}

PYPI_UV_URL = "https://pypi.org/pypi/uv/json"

HTTP_TIMEOUT = 30.0


class SubSection(TypedDict):
    """A titled sub-block of documentation within a section."""

    title: str
    content: list[str]


class DocumentationElement(TypedDict):
    """A single documented command, setting, or resolver concept."""

    name: str
    description: str
    documentation: list[SubSection]


async def _read_json(path: Path) -> dict[str, Any]:
    """Read a JSON file, returning {} on any failure."""
    try:
        return json.loads(await asyncio.to_thread(path.read_text))
    except (OSError, json.JSONDecodeError):
        return {}


async def _write_json(path: Path, data: dict[str, Any]) -> None:
    """Write a JSON file atomically."""
    await asyncio.to_thread(path.write_text, json.dumps(data, indent=2))


async def _fetch_text(url: str) -> str:
    """Fetch a URL and return the response body as text."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=HTTP_TIMEOUT) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


def clean_text(text: str) -> str:
    """Normalize Unicode text, curly quotes, and whitespace."""
    text = unicodedata.normalize("NFKC", text)
    replacements = {
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u2013": "-",
        "\n": " ",
        "\t": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return " ".join(text.split()).strip()


def clean_code(text: str) -> str:
    """Normalize code text while preserving newlines and indentation."""
    text = unicodedata.normalize("NFKC", text)
    return text.replace("\t", "    ").strip()


def _slugify(text: str) -> str:
    """Convert a section name into a URI-safe slug."""
    return text.lower().replace(" ", "-")


def _has_class(element: Any, class_name: str) -> bool:
    """Return whether a BeautifulSoup element has a CSS class."""
    classes = element.get("class") or []
    return class_name in classes


def parse_cli_documentation(html: str) -> dict[str, Any]:
    """Parse the CLI reference page into structured elements."""
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one(".md-content")
    if content is None:
        return {}

    elements: list[DocumentationElement] = []
    for section in content.find_all("h2"):
        command_name = clean_text(section.get_text(strip=True))
        paragraph = section.find_next("p")
        description = clean_text(paragraph.get_text(strip=True) if paragraph else "")

        documentation: list[SubSection] = []
        current_subsection: SubSection | None = None
        general_content: list[str] = []
        options_content: list[str] = []

        next_elem = section.find_next_sibling()
        while next_elem and next_elem.name != "h2":
            if next_elem.name in ("h3", "h4"):
                if general_content:
                    documentation.append(
                        {"title": "General", "content": general_content}
                    )
                    general_content = []
                current_subsection = {
                    "title": clean_text(next_elem.get_text(strip=True)),
                    "content": [],
                }
                documentation.append(current_subsection)
            elif next_elem.name in ("p", "pre", "ul", "ol"):
                text = clean_text(next_elem.get_text(strip=True))
                if text:
                    if current_subsection is not None:
                        current_subsection["content"].append(text)
                    else:
                        general_content.append(text)
            elif next_elem.name == "dl":
                for dt, dd in zip(
                    next_elem.find_all("dt"), next_elem.find_all("dd"), strict=False
                ):
                    option_name = clean_text(dt.get_text(strip=True))
                    option_desc = clean_text(dd.get_text(strip=True))
                    options_content.append(f"{option_name}: {option_desc}")
            next_elem = next_elem.find_next_sibling()

        if general_content:
            documentation.append({"title": "General", "content": general_content})
        if options_content:
            documentation.append({"title": "Options", "content": options_content})

        documentation = [s for s in documentation if s["content"]]
        elements.append(
            {
                "name": command_name,
                "description": description,
                "documentation": documentation,
            }
        )

    return {"type": "documentation_section", "section": "cli", "elements": elements}


def parse_settings_documentation(html: str) -> dict[str, Any]:
    """Parse the settings reference page into structured elements."""
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one(".md-content")
    if content is None:
        return {}

    elements: list[DocumentationElement] = []
    for section in content.find_all("h2"):
        setting_name = clean_text(section.get_text(strip=True))
        paragraph = section.find_next("p")
        description = clean_text(paragraph.get_text(strip=True) if paragraph else "")

        documentation: list[SubSection] = []
        current_subsection: SubSection | None = None
        general_content: list[str] = []

        next_elem = section.find_next_sibling()
        while next_elem and next_elem.name != "h2":
            if next_elem.name in ("h3", "h4"):
                if general_content:
                    documentation.append(
                        {"title": "General", "content": general_content}
                    )
                    general_content = []
                current_subsection = {
                    "title": clean_text(next_elem.get_text(strip=True)),
                    "content": [],
                }
                documentation.append(current_subsection)
            elif next_elem.name in ("p", "ul", "ol"):
                text = clean_text(next_elem.get_text(strip=True))
                if text:
                    if current_subsection is not None:
                        current_subsection["content"].append(text)
                    else:
                        general_content.append(text)
            elif next_elem.name == "div" and any(
                _has_class(next_elem, cls) for cls in ("highlight", "highlight-default")
            ):
                pre_tag = next_elem.find("pre")
                if pre_tag is not None:
                    example_text = clean_code(pre_tag.get_text("\n", strip=True))
                    if current_subsection is not None:
                        current_subsection["content"].append(
                            f"Example:\n{example_text}"
                        )
                    else:
                        general_content.append(f"Example:\n{example_text}")
            next_elem = next_elem.find_next_sibling()

        if general_content:
            documentation.append({"title": "General", "content": general_content})
        documentation = [s for s in documentation if s["content"]]
        elements.append(
            {
                "name": setting_name,
                "description": description,
                "documentation": documentation,
            }
        )

    return {
        "type": "documentation_section",
        "section": "settings",
        "elements": elements,
    }


def parse_resolver_documentation(html: str) -> dict[str, Any]:
    """Parse the resolver internals reference page into structured elements."""
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one(".md-content")
    if content is None:
        return {}

    elements: list[DocumentationElement] = []
    for section in content.find_all("h2"):
        resolver_name = clean_text(section.get_text(strip=True))

        description_parts: list[str] = []
        description_elem = section.find_next_sibling()
        while description_elem and description_elem.name not in ("h2", "h3", "h4"):
            if (
                description_elem.name == "p"
                or description_elem.name == "div"
                and _has_class(description_elem, "admonition")
            ):
                text = clean_text(description_elem.get_text(strip=True))
                if text:
                    description_parts.append(text)
            elif description_elem.name in ("ul", "ol"):
                for li in description_elem.find_all("li"):
                    text = clean_text(li.get_text(strip=True))
                    if text:
                        description_parts.append(f"- {text}")
            description_elem = description_elem.find_next_sibling()

        documentation: list[SubSection] = []
        current_subsection: SubSection | None = None
        general_content: list[str] = []

        next_elem = section.find_next_sibling()
        while next_elem and next_elem.name != "h2":
            if next_elem.name in ("h3", "h4"):
                if general_content:
                    documentation.append(
                        {"title": "General", "content": general_content}
                    )
                    general_content = []
                current_subsection = {
                    "title": clean_text(next_elem.get_text(strip=True)),
                    "content": [],
                }
                documentation.append(current_subsection)
            elif next_elem.name in ("p", "ul", "ol"):
                text = clean_text(next_elem.get_text(strip=True))
                if text:
                    if current_subsection is not None:
                        current_subsection["content"].append(text)
                    else:
                        general_content.append(text)
            elif next_elem.name == "div" and any(
                _has_class(next_elem, cls) for cls in ("highlight", "highlight-default")
            ):
                pre_tag = next_elem.find("pre")
                if pre_tag is not None:
                    example_text = clean_code(pre_tag.get_text("\n", strip=True))
                    if current_subsection is not None:
                        current_subsection["content"].append(
                            f"Example:\n{example_text}"
                        )
                    else:
                        general_content.append(f"Example:\n{example_text}")
            next_elem = next_elem.find_next_sibling()

        if general_content:
            documentation.append({"title": "General", "content": general_content})
        documentation = [s for s in documentation if s["content"]]
        elements.append(
            {
                "name": resolver_name,
                "description": " ".join(description_parts).strip(),
                "documentation": documentation,
            }
        )

    return {
        "type": "documentation_section",
        "section": "resolver",
        "elements": elements,
    }


def _section_parser(section: str):
    """Return the parser for a documentation section."""
    return {
        "cli": parse_cli_documentation,
        "settings": parse_settings_documentation,
        "resolver": parse_resolver_documentation,
    }[section]


class CacheManager:
    """Manage UV documentation cache storage and retrieval."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        if cache_dir is None:
            cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
            cache_dir = cache_root / "uv-mcp" / "docs"
        self.cache_dir = cache_dir
        self.version_file = self.cache_dir / "version.json"

    async def initialize(self) -> None:
        """Initialize the cache, fetching documentation if it is missing."""
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

    async def update_section(self, section: str, content: dict[str, Any]) -> None:
        """Update the cache for a documentation section."""
        await _write_json(self.get_section_cache_path(section), content)

    async def clear_cache(self) -> None:
        """Clear all cached documentation."""
        for file in self.cache_dir.glob("*.json"):
            await asyncio.to_thread(file.unlink)

    async def is_cache_valid(self) -> bool:
        """Check whether the cache matches the current UV version."""
        try:
            current_version = await self.fetch_current_version()
            cached_version = await self.get_cached_version()
            return cached_version.get("version") == current_version.get("version")
        except Exception:
            logger.exception("Failed to check cache validity")
            return False

    async def fetch_current_version(self) -> dict[str, str]:
        """Fetch the current UV version from PyPI."""
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=HTTP_TIMEOUT
        ) as client:
            response = await client.get(PYPI_UV_URL)
            if response.status_code == 200:
                data = response.json()
                if "info" in data and "version" in data["info"]:
                    return {"version": data["info"]["version"]}
        return {"version": "unknown"}

    async def fetch_section(self, section: str) -> dict[str, Any]:
        """Fetch and parse a documentation section from the UV docs website."""
        url = DOCS_URLS[section]
        return _section_parser(section)(await _fetch_text(url))

    async def get_section_overview(self, section: str) -> dict[str, Any]:
        """Return a section's command list, or raise if it is not cached."""
        cached_content = await self.get_cached_section(section)
        elements = cached_content.get("elements", [])
        if not elements:
            raise FileNotFoundError(
                f"Documentation for '{section}' is not cached; run update_cache first"
            )
        return {
            "type": "section",
            "name": section,
            "commands": [
                {
                    "name": element["name"],
                    "description": element["description"],
                    "uri": f"uv:docs://{section}/{_slugify(element['name'])}",
                }
                for element in elements
            ],
        }

    async def get_command_docs(self, section: str, command: str) -> dict[str, Any]:
        """Return metadata and subsection links for a command."""
        element = await self._find_element(section, command)
        return {
            "type": "command",
            "name": element["name"],
            "description": element["description"],
            "sections": [
                {
                    "title": doc["title"],
                    "uri": (
                        f"uv:docs://{section}/{_slugify(element['name'])}"
                        f"/{_slugify(doc['title'])}"
                    ),
                }
                for doc in element.get("documentation", [])
            ],
        }

    async def get_subsection_docs(
        self, section: str, command: str, subsection: str
    ) -> dict[str, Any]:
        """Return the detailed content of a command subsection."""
        element = await self._find_element(section, command)
        for doc in element.get("documentation", []):
            if doc["title"].lower() == subsection.replace("-", " ").lower():
                return {
                    "type": "section",
                    "command": element["name"],
                    "section": doc["title"],
                    "content": doc.get("content", []),
                }
        raise ValueError(
            f"Section '{subsection}' not found in command '{element['name']}'"
        )

    async def _find_element(self, section: str, command: str) -> dict[str, Any]:
        """Find a documented element by name within a cached section."""
        cached_content = await self.get_cached_section(section)
        elements = cached_content.get("elements", [])
        if not elements:
            raise FileNotFoundError(
                f"Documentation for '{section}' is not cached; run update_cache first"
            )
        lookup = command.replace("-", " ")
        if section == "cli" and not lookup.startswith("uv "):
            lookup = f"uv {lookup}"
        for element in elements:
            if element["name"].lower() == lookup.lower():
                return element
        raise ValueError(f"Command '{command}' not found in section '{section}'")

    async def search(self, query: str) -> list[dict[str, str]]:
        """Search cached documentation, returning the best matching resources."""
        keywords = [keyword.lower() for keyword in query.split()]

        def calculate_relevance(resource: dict[str, Any], words: list[str]) -> float:
            score = 0.0
            search_text = resource["search_text"].lower()
            section = resource["section"]
            name = resource["name"].lower()

            for keyword in words:
                if keyword == section:
                    score += 3.0
                elif keyword in section:
                    score += 2.0
                if keyword == name:
                    score += 2.0
                elif keyword in name:
                    score += 1.0

            for keyword in words:
                if f" {keyword} " in f" {search_text} ":
                    score += 0.75
                elif keyword in search_text:
                    score += 0.5

            if score < 1.0:
                for keyword in words:
                    if get_close_matches(keyword, [name, section], n=1, cutoff=0.6):
                        score += 0.25
            return score

        resources: list[dict[str, Any]] = []
        for section in DOCUMENTATION_SECTIONS:
            section_data = await self.get_cached_section(section)
            for element in section_data.get("elements", []):
                name = element["name"]
                description = element["description"]
                subsections = [
                    doc["title"]
                    for doc in element.get("documentation", [])
                    if doc.get("title") not in ("General", "Options")
                ]
                content_text = " ".join(
                    str(item)
                    for doc in element.get("documentation", [])
                    for item in doc.get("content", [])[:3]
                )
                resources.append(
                    {
                        "path": f"uv:docs://{section}/{_slugify(name)}",
                        "name": name,
                        "description": description,
                        "search_text": (
                            f"{name} {description} "
                            f"{', '.join(subsections)} {content_text}"
                        ),
                        "section": section,
                    }
                )

        results = []
        for resource in resources:
            if (score := calculate_relevance(resource, keywords)) > 0.25:
                results.append(
                    (
                        score,
                        {
                            "path": resource["path"],
                            "name": resource["name"],
                            "description": resource["description"],
                        },
                    )
                )
        results.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in results[:3]]
