# UV Project Setup Reference

## New Project

```bash
uv init my-project && cd my-project
uv add requests fastapi
uv run python main.py
```

## Virtual Environment

```bash
uv venv
source .venv/bin/activate
uv sync
```

## Python Versions

```bash
uv python install 3.14
uv python pin 3.14
```

## Inline Script Metadata (PEP 723)

```python
# /// script
# dependencies = ["requests>=2.28.0"]
# requires-python = ">=3.14"
# ///
import requests
```

Run: `uv run script.py` (auto-installs dependencies)
