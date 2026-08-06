"""Tools for the cached UV documentation resources."""

from fastmcp import Context

from uv_mcp.app import app
from uv_mcp.docs import DOCUMENTATION_SECTIONS
from uv_mcp.tools.common import services


@app.prompt(name="summarize_docs")
async def summarize_docs(ctx: Context, section: str | None = None) -> str:
    """Generate a prompt for summarizing cached UV documentation.

    Args:
        section: Optional documentation section, such as ``cli``.
        ctx: FastMCP request context.

    Returns:
        A prompt instructing a model how to summarize the documentation.
    """
    if section:
        overview = await services(ctx).docs.get_section_overview(section)
        commands = ", ".join(command["name"] for command in overview["commands"])
        target = f"the `{overview['name']}` section, covering {commands}"
    else:
        target = "the cached UV documentation"
    return (
        "Summarize "
        f"{target} for a Python developer. Use the available uv:docs:// resources "
        "to read the relevant documentation. Explain the purpose, key commands "
        "or settings, important options, and concise usage examples in Markdown."
    )


@app.tool(name="update_cache")
async def update_cache(ctx: Context, force: bool = False) -> str:
    """Update the cached UV documentation.

    Args:
        force: Refresh even when the cached UV version matches.
        ctx: FastMCP request context.

    Returns:
        Update summary.
    """
    docs = services(ctx).docs
    if not force and await docs.is_cache_valid():
        return "Documentation cache is up to date with the current UV version."
    version_info = await docs.fetch_current_version()
    results: list[str] = []
    for section in DOCUMENTATION_SECTIONS:
        try:
            content = await docs.fetch_section(section)
            await docs.update_section(section, content)
            results.append(
                f"- {section.title()}: {len(content.get('elements', []))} elements"
            )
        except Exception as e:
            results.append(f"- {section.title()}: failed ({e})")
    await docs.update_version(version_info)
    return "Documentation cache updated:\n" + "\n".join(results)


@app.tool(name="search_documentation")
async def search_documentation(query: str, ctx: Context) -> str:
    """Search cached UV documentation.

    Args:
        query: Search query.
        ctx: FastMCP request context.

    Returns:
        Best matching documentation resources.
    """
    results = await services(ctx).docs.search(query)
    if not results:
        return "No matching documentation resources found."
    formatted = "\n\n".join(
        f"Resource: {result['path']}\n"
        f"Name: {result['name']}\n"
        f"Description: {result['description']}"
        for result in results
    )
    return f"Best matching resources:\n\n{formatted}"
