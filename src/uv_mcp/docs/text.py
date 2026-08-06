import re
import unicodedata
from functools import cache

_CLEAN_TEXT_TABLE = str.maketrans(
    {
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u2013": "-",
        "\n": " ",
        "\t": " ",
    }
)


def clean_text(text: str) -> str:
    """Normalize Unicode text, punctuation, and whitespace."""
    normalized = unicodedata.normalize("NFKC", text).translate(_CLEAN_TEXT_TABLE)

    return " ".join(normalized.split())


def clean_code(text: str) -> str:
    """Normalize code text while preserving newlines and indentation."""
    return unicodedata.normalize("NFKC", text).replace("\t", "    ").strip()


@cache
def slugify(text: str) -> str:
    """Convert a heading into a URI-safe slug."""
    return re.sub(r"\s+", "-", text.strip().lower())
