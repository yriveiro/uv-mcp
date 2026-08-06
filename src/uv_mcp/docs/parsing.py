from dataclasses import dataclass
from typing import Literal, TypedDict

from bs4 import BeautifulSoup, Tag

from uv_mcp.docs.constants import Section
from uv_mcp.docs.text import clean_code, clean_text

_GENERAL = "General"
_OPTIONS = "Options"
_TEXT_TAGS = ("p", "ul", "ol")
_HEADING_TAGS = ("h3", "h4")
_HIGHLIGHT_CLASSES = ("highlight", "highlight-default")
_ADMONITION_CLASS = "admonition"


class SubSection(TypedDict):
    """A titled block of documentation content within an element."""

    title: str
    content: list[str]


class DocumentationElement(TypedDict):
    """A documented command, setting, or resolver concept."""

    name: str
    description: str
    documentation: list[SubSection]


class SectionPayload(TypedDict):
    """Parsed contents of one documentation reference page."""

    type: Literal["documentation_section"]
    section: Section
    elements: list[DocumentationElement]


@dataclass(frozen=True, slots=True)
class SectionSpec:
    """Parsing rules for a documentation reference page."""

    name: Section
    handle_options: bool = False
    handle_code: bool = False
    handle_pre: bool = False


SECTION_SPECS: dict[Section, SectionSpec] = {
    "cli": SectionSpec("cli", handle_options=True, handle_pre=True),
    "settings": SectionSpec("settings", handle_code=True),
    "resolver": SectionSpec("resolver", handle_code=True),
}


def parse_section(html: str, spec: SectionSpec) -> SectionPayload:
    """Parse a documentation reference page into structured elements."""
    content = _content_root(html)
    if content is None:
        return {"type": "documentation_section", "section": spec.name, "elements": []}

    return {
        "type": "documentation_section",
        "section": spec.name,
        "elements": [_element(heading, spec) for heading in content.find_all("h2")],
    }


def parse_cli_documentation(html: str) -> SectionPayload:
    """Parse the CLI reference page."""
    return parse_section(html, SECTION_SPECS["cli"])


def parse_settings_documentation(html: str) -> SectionPayload:
    """Parse the settings reference page."""
    return parse_section(html, SECTION_SPECS["settings"])


def parse_resolver_documentation(html: str) -> SectionPayload:
    """Parse the resolver internals reference page."""
    return parse_section(html, SECTION_SPECS["resolver"])


def _content_root(html: str) -> Tag | None:
    soup = BeautifulSoup(html, "html.parser")

    return soup.select_one(".md-content")


def _element(heading: Tag, spec: SectionSpec) -> DocumentationElement:
    name = clean_text(heading.get_text(strip=True))

    return {
        "name": name,
        "description": _description(heading, spec),
        "documentation": _collect_documentation(heading, spec),
    }


def _description(heading: Tag, spec: SectionSpec) -> str:
    if spec.name == "resolver":
        return _resolver_description(heading)

    paragraph = heading.find_next("p")
    if paragraph is None:
        return ""

    return clean_text(paragraph.get_text(strip=True))


def _resolver_description(heading: Tag) -> str:
    parts: list[str] = []
    for sibling in heading.find_next_siblings():
        if sibling.name in ("h2", "h3", "h4"):
            break
        if sibling.name == "p" or (
            sibling.name == "div" and _has_class(sibling, _ADMONITION_CLASS)
        ):
            if text := clean_text(sibling.get_text(strip=True)):
                parts.append(text)
        elif sibling.name in ("ul", "ol"):
            parts.extend(f"- {item}" for item in _list_items(sibling))

    return " ".join(parts).strip()


def _list_items(list_tag: Tag) -> list[str]:
    return [
        item
        for list_item in list_tag.find_all("li")
        if (item := clean_text(list_item.get_text(strip=True)))
    ]


def _collect_documentation(heading: Tag, spec: SectionSpec) -> list[SubSection]:
    documentation: list[SubSection] = []
    general: list[str] = []
    options: list[str] = []
    current: SubSection | None = None

    for sibling in heading.find_next_siblings():
        if sibling.name == "h2":
            break
        if sibling.name in _HEADING_TAGS:
            if general:
                documentation.append({"title": _GENERAL, "content": general})
                general = []
            current = {"title": clean_text(sibling.get_text(strip=True)), "content": []}
            documentation.append(current)
            continue
        if sibling.name in _TEXT_TAGS or (spec.handle_pre and sibling.name == "pre"):
            if text := clean_text(sibling.get_text(strip=True)):
                _append_text(current, general, text)
            continue
        if spec.handle_options and sibling.name == "dl":
            options.extend(_options_from(sibling))
            continue
        if (
            spec.handle_code
            and _has_any_class(sibling, *_HIGHLIGHT_CLASSES)
            and (example := _example(sibling))
        ):
            _append_text(current, general, f"Example:\n{example}")

    if general:
        documentation.append({"title": _GENERAL, "content": general})
    if options:
        documentation.append({"title": _OPTIONS, "content": options})

    return [subsection for subsection in documentation if subsection["content"]]


def _append_text(current: SubSection | None, general: list[str], text: str) -> None:
    if current is not None:
        current["content"].append(text)
    else:
        general.append(text)


def _options_from(definition_list: Tag) -> list[str]:
    return [
        f"{clean_text(dt.get_text(strip=True))}: {clean_text(dd.get_text(strip=True))}"
        for dt, dd in zip(
            definition_list.find_all("dt"),
            definition_list.find_all("dd"),
            strict=False,
        )
    ]


def _example(container: Tag) -> str | None:
    pre = container.find("pre")
    if pre is None:
        return None

    return clean_code(pre.get_text("\n", strip=True))


def _has_class(element: Tag, class_name: str) -> bool:
    return class_name in (element.get("class") or ())


def _has_any_class(element: Tag, *class_names: str) -> bool:
    return any(_has_class(element, name) for name in class_names)
