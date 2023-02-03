import subprocess
import sys
import tempfile
import urllib.request
import venv
from pathlib import Path

import change_wheel_version


def get_installed_version(python: Path, dist: str = "pypyp") -> bytes:
    prog = f"import importlib.metadata; print(importlib.metadata.version('{dist}'))"
    return subprocess.check_output([python, "-c", prog]).strip()


PYP_DIST = "pypyp"
PYP_V1_WHEEL = "https://files.pythonhosted.org/packages/ad/c2/92fa4ab416c7f697a2944d54c6e58ed5d043e296f6f671af32aaacb4b40e/pypyp-1.0.0-py3-none-any.whl"  # noqa: E501


def test_change_wheel_version_pip() -> None:
    assert sys.version_info >= (3, 9)

    with tempfile.TemporaryDirectory() as _tmpdir:
        tmpdir = Path(_tmpdir)

        original_wheel = tmpdir / Path(PYP_V1_WHEEL).name
        urllib.request.urlretrieve(PYP_V1_WHEEL, original_wheel)

        venv.create(tmpdir / "venv", with_pip=True, clear=True)
        pip = tmpdir / "venv" / "bin" / "pip"
        python = tmpdir / "venv" / "bin" / "python"

        subprocess.check_call([pip, "install", "--upgrade", "pip"])

        subprocess.check_call([pip, "install", original_wheel])
        assert get_installed_version(python) == b"1.0.0"

        # change the wheel
        changed_wheel = change_wheel_version.change_wheel_version(original_wheel, None, "yikes")
        subprocess.check_call([pip, "install", changed_wheel])
        assert get_installed_version(python) == b"1.0.0+yikes"

        # change it back
        subprocess.check_call([pip, "install", original_wheel])
        assert get_installed_version(python) == b"1.0.0"

        # change the wheel again
        changed_wheel = change_wheel_version.change_wheel_version(original_wheel, "2.0.0", None)
        subprocess.check_call([pip, "install", changed_wheel])
        assert get_installed_version(python) == b"2.0.0"

        # change the wheel againx2
        changed_wheel = change_wheel_version.change_wheel_version(original_wheel, "3.0.0", "yikes")
        subprocess.check_call([pip, "install", changed_wheel])
        assert get_installed_version(python) == b"3.0.0+yikes"

        # change the wheel but with a long version
        version = "super.long.version.string.that.is.longer.than.sixty.eight.characters.even.eighty"
        assert len(version) == 80
        changed_wheel = change_wheel_version.change_wheel_version(original_wheel, "1", version)
        subprocess.check_call([pip, "install", changed_wheel])
        assert get_installed_version(python) == b"1+" + version.encode("utf-8")


def test_change_wheel_version_installer() -> None:
    assert sys.version_info >= (3, 9)

    with tempfile.TemporaryDirectory() as _tmpdir:
        tmpdir = Path(_tmpdir)

        original_wheel = tmpdir / Path(PYP_V1_WHEEL).name
        urllib.request.urlretrieve(PYP_V1_WHEEL, original_wheel)

        venv.create(tmpdir / "venv", with_pip=True, clear=True)
        pip = tmpdir / "venv" / "bin" / "pip"
        python = tmpdir / "venv" / "bin" / "python"

        subprocess.check_call([pip, "install", "--upgrade", "pip", "installer"])

        # change the wheel
        changed_wheel = change_wheel_version.change_wheel_version(original_wheel, None, "yikes")
        subprocess.check_call([python, "-m", "installer", changed_wheel])
        assert get_installed_version(python) == b"1.0.0+yikes"

        subprocess.check_call([pip, "uninstall", "-y", PYP_DIST])

        # change the wheel but with a long version
        version = "super.long.version.string.that.is.longer.than.sixty.eight.characters.even.eighty"
        assert len(version) == 80
        changed_wheel = change_wheel_version.change_wheel_version(original_wheel, "1", version)
        subprocess.check_call([python, "-m", "installer", changed_wheel])
        assert get_installed_version(python) == b"1+" + version.encode("utf-8")
