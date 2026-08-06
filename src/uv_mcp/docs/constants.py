from typing import Literal

type Section = Literal["cli", "settings", "resolver"]

DOCUMENTATION_SECTIONS: tuple[Section, ...] = ("cli", "settings", "resolver")

DOCS_URLS: dict[Section, str] = {
    "cli": "https://docs.astral.sh/uv/reference/cli/",
    "settings": "https://docs.astral.sh/uv/reference/settings/",
    "resolver": "https://docs.astral.sh/uv/reference/resolver-internals/",
}

PYPI_UV_URL = "https://pypi.org/pypi/uv/json"
HTTP_TIMEOUT = 30.0
VERSION_FILE = "version.json"
