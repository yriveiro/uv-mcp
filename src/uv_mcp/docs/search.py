from collections.abc import Awaitable, Callable
from difflib import get_close_matches
from typing import Any

from uv_mcp.docs.constants import DOCUMENTATION_SECTIONS
from uv_mcp.docs.parsing import DocumentationElement
from uv_mcp.docs.text import slugify

_EXCLUDED_TITLES = {"General", "Options"}
_SNIPPET_LINES = 3
_MIN_SCORE = 0.25
_MAX_RESULTS = 3


def build_resources(
    elements: list[DocumentationElement], section: str
) -> list[dict[str, Any]]:
    """Flatten a cached section into searchable resources."""
    resources: list[dict[str, Any]] = []
    for element in elements:
        name = element["name"]
        subsections = [
            doc["title"]
            for doc in element.get("documentation", [])
            if doc.get("title") not in _EXCLUDED_TITLES
        ]
        content = " ".join(
            str(item)
            for doc in element.get("documentation", [])
            for item in doc.get("content", [])[:_SNIPPET_LINES]
        )
        resources.append(
            {
                "path": f"uv:docs://{section}/{slugify(name)}",
                "name": name,
                "description": element["description"],
                "search_text": (
                    f"{name} {element['description']} "
                    f"{', '.join(subsections)} {content}"
                ),
                "section": section,
            }
        )

    return resources


def score_resource(resource: dict[str, Any], keywords: list[str]) -> float:
    """Score a resource against search keywords."""
    score = 0.0
    section = resource["section"]
    name = resource["name"].lower()
    search_text = resource["search_text"].lower()

    for keyword in keywords:
        if keyword == section:
            score += 3.0
        elif keyword in section:
            score += 2.0
        if keyword == name:
            score += 2.0
        elif keyword in name:
            score += 1.0

    for keyword in keywords:
        if f" {keyword} " in f" {search_text} ":
            score += 0.75
        elif keyword in search_text:
            score += 0.5

    if score < 1.0:
        score += sum(
            0.25
            for keyword in keywords
            if get_close_matches(keyword, [name, section], n=1, cutoff=0.6)
        )

    return score


async def search_sections(
    load_section: Callable[[str], Awaitable[dict[str, Any]]], query: str
) -> list[dict[str, str]]:
    """Search all cached sections and return the best matching resources."""
    keywords = query.lower().split()
    resources = [
        resource
        for section in DOCUMENTATION_SECTIONS
        for resource in build_resources(
            (await load_section(section)).get("elements", []), section
        )
    ]
    ranked = sorted(
        ((score_resource(resource, keywords), resource) for resource in resources),
        key=lambda item: item[0],
        reverse=True,
    )
    matches = [
        {
            "path": resource["path"],
            "name": resource["name"],
            "description": resource["description"],
        }
        for score, resource in ranked
        if score > _MIN_SCORE
    ]

    return matches[:_MAX_RESULTS]
