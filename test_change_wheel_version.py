import os
import subprocess
import sys
import tempfile
import urllib.request
import venv
from email import message_from_bytes
from email.message import Message
from pathlib import Path

import pytest
from packaging import tags

import change_wheel_version


def get_installed_version(python: Path, dist: str = "pypyp") -> bytes:
    prog = f"import importlib.metadata; print(importlib.metadata.version('{dist}'))"
    return subprocess.check_output([python, "-c", prog]).strip()


def get_wheel_metadata(python: Path, dist: str) -> Message:
    prog = (
        "import importlib.metadata; "
        + f" print(importlib.metadata.distribution('{dist}').read_text('WHEEL'))"
    )
    wheel_metadata = subprocess.check_output([python, "-c", prog], text=False).strip()
    return message_from_bytes(wheel_metadata)


# PyPI in practice doesn't break links. They do make this pretty redirect available too.
# PYP_V1_WHEEL = "https://files.pythonhosted.org/packages/py3/p/pypyp/pypyp-1.0.0-py3-none-any.whl"
PYP_V1_WHEEL = "https://files.pythonhosted.org/packages/ad/c2/92fa4ab416c7f697a2944d54c6e58ed5d043e296f6f671af32aaacb4b40e/pypyp-1.0.0-py3-none-any.whl"  # noqa: E501
PYP_DIST = "pypyp"


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


def test_preserves_permissions() -> None:
    with tempfile.TemporaryDirectory() as _tmpdir:
        tmpdir = Path(_tmpdir)

        venv.create(tmpdir / "venv", with_pip=True, clear=True)
        pip = tmpdir / "venv" / "bin" / "pip"
        python = tmpdir / "venv" / "bin" / "python"

        subprocess.check_call([pip, "install", "--upgrade", "pip"])

        subprocess.check_call([pip, "wheel", "regex==2022.10.31", "-w", str(tmpdir)])
        original_wheel = list(tmpdir.glob("regex-*.whl"))[0]

        subprocess.check_call([pip, "install", original_wheel])
        assert get_installed_version(python, dist="regex") == b"2022.10.31"

        executable_files_before = [
            p for p in (tmpdir / "venv/lib").rglob("*") if p.is_file() and os.access(p, os.X_OK)
        ]

        changed_wheel = change_wheel_version.change_wheel_version(original_wheel, None, "yikes")
        subprocess.check_call([pip, "install", changed_wheel])
        assert get_installed_version(python, dist="regex") == b"2022.10.31+yikes"

        executable_files_after = [
            p for p in (tmpdir / "venv/lib").rglob("*") if p.is_file() and os.access(p, os.X_OK)
        ]
        assert executable_files_before == executable_files_after


def test_change_platform() -> None:
    with tempfile.TemporaryDirectory() as _tmpdir:
        tmpdir = Path(_tmpdir)

        original_wheel = tmpdir / Path(PYP_V1_WHEEL).name
        urllib.request.urlretrieve(PYP_V1_WHEEL, original_wheel)

        venv.create(tmpdir / "venv", with_pip=True, clear=True)
        pip = tmpdir / "venv" / "bin" / "pip"
        python = tmpdir / "venv" / "bin" / "python"

        subprocess.check_call([pip, "install", "--upgrade", "pip"])

        # This is an arbitrary platform-dependent tag. Anything valid other than "py3-none-any"
        # (which pypyp has) would be fine for testing.
        binary_tag = str(next(tags.sys_tags()))
        assert "none" not in binary_tag

        # Change the wheel to have a platform tag of `binary_tag` and install it.
        changed_wheel = change_wheel_version.change_wheel_version(
            original_wheel, version=None, local_version=None, platform_tag=binary_tag
        )
        subprocess.check_call([pip, "install", changed_wheel])

        # The original was pure python. Check that, as installed, it is platform-specific.
        wheel_metadata = get_wheel_metadata(python, "pypyp")
        assert wheel_metadata["Tag"] == binary_tag
        assert wheel_metadata["Root-Is-Purelib"] == "false"

        # Check that a suitable error is raised with an internally-inconsistent platform tag.
        with pytest.raises(ValueError, match="ABI and platform are inconsistent"):
            change_wheel_version.change_wheel_version(
                original_wheel, version=None, local_version=None, platform_tag="cp311-cp311-any"
            )

        # Check that a suitable error is raised with an unparseable platform tag.
        with pytest.raises(ValueError, match=r"too many values to unpack \(expected 3\)"):
            change_wheel_version.change_wheel_version(
                original_wheel, version=None, local_version=None, platform_tag="py3-none-any-some"
            )
