import shutil

import pytest

from uv_mcp.uv_wrapper import UVWrapper

pytestmark = pytest.mark.skipif(
    shutil.which("uv") is None, reason="uv is not installed"
)


def test_create_and_list_virtualenv(tmp_path) -> None:
    venv_path = tmp_path / ".venv"
    wrapper = UVWrapper()

    wrapper.create_virtualenv(str(venv_path))
    packages = wrapper.list_packages_in_venv(str(venv_path))

    assert venv_path.is_dir()
    assert isinstance(packages, list)
