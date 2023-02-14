import argparse
import email.parser
import email.policy
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Optional, no_type_check

import installer.utils
import packaging.version


def version_replace(v: packaging.version.Version, **kwargs: Any) -> packaging.version.Version:
    # yikes :-)
    self = packaging.version.Version.__new__(packaging.version.Version)
    self._version = v._version._replace(**kwargs)
    return packaging.version.Version(str(self))


class ExecutablePreservingZipfile(zipfile.ZipFile):
    @no_type_check
    def _extract_member(self, member, targetpath, pwd):
        if not isinstance(member, zipfile.ZipInfo):
            member = self.getinfo(member)

        targetpath = super()._extract_member(member, targetpath, pwd)

        mode = member.external_attr >> 16
        if mode != 0:
            os.chmod(targetpath, mode)
        return targetpath


def wheel_unpack(wheel: Path, dest_dir: Path, name_ver: str) -> None:
    # This is the moral equivalent of:
    # subprocess.check_output(
    #     [sys.executable, "-m", "wheel", "unpack", "-d", str(dest_dir), str(wheel)]
    # )
    # Except we need to preserve permissions
    # https://github.com/pypa/wheel/issues/505
    with ExecutablePreservingZipfile(wheel) as wf:
        wf.extractall(dest_dir / name_ver)


def change_wheel_version(
    wheel: Path,
    version: Optional[str],
    local_version: Optional[str],
    allow_same_version: bool = False,
) -> Path:
    old_parts = installer.utils.parse_wheel_filename(wheel.name)
    old_version = packaging.version.Version(old_parts.version)
    distribution = old_parts.distribution

    if version is None:
        # just replace the local version
        assert local_version is not None
        new_version = version_replace(
            old_version, local=packaging.version._parse_local_version(local_version)
        )
    else:
        # replace the base version and (possibly) the local version
        new_version = packaging.version.Version(version)
        assert not new_version.local
        if local_version:
            new_version = version_replace(
                new_version, local=packaging.version._parse_local_version(local_version)
            )

    if version == old_version:
        if allow_same_version:
            return wheel
        raise ValueError(f"Version {version} is the same as the old version")

    with tempfile.TemporaryDirectory() as _tmpdir:
        tmpdir = Path(_tmpdir)
        dest_dir = tmpdir / "wheel"

        wheel_unpack(wheel, dest_dir, f"{distribution}-{old_version}")

        old_slug = f"{distribution}-{old_version}"
        new_slug = f"{distribution}-{new_version}"
        assert (dest_dir / old_slug).exists()
        assert (dest_dir / old_slug / f"{old_slug}.dist-info").exists()

        # copy everything over
        shutil.move(dest_dir / old_slug, dest_dir / new_slug)

        # rename dist-info
        shutil.move(
            dest_dir / new_slug / f"{old_slug}.dist-info",
            dest_dir / new_slug / f"{new_slug}.dist-info",
        )
        # rename data
        if (dest_dir / new_slug / f"{old_slug}.data").exists():
            shutil.move(
                dest_dir / new_slug / f"{old_slug}.data", dest_dir / new_slug / f"{new_slug}.data"
            )

        metadata = dest_dir / new_slug / f"{new_slug}.dist-info" / "METADATA"

        # This is actually a non-conformant email policy as per
        # https://packaging.python.org/en/latest/specifications/core-metadata/
        # However, it works around this bug in setuptools in cases where the version is really long
        # https://github.com/pypa/setuptools/issues/3808
        max_line_length = 200
        policy = email.policy.compat32.clone(max_line_length=200)
        version_str = str(new_version)
        if len(version_str) >= max_line_length:
            raise ValueError(f"Version {version_str} is too long")

        with open(metadata, "rb") as f:
            parser = email.parser.BytesParser(policy=policy)
            msg = parser.parse(f)

        msg.replace_header("Version", version_str)
        with open(metadata, "wb") as f:
            f.write(msg.as_bytes())

        # wheel pack rewrites the RECORD file
        subprocess.check_output(
            [
                sys.executable,
                "-m",
                "wheel",
                "pack",
                "-d",
                str(wheel.parent),
                str(dest_dir / new_slug),
            ]
        )

    # wheel pack sorts the tag, so we need to do the same
    new_tag = "-".join(".".join(sorted(t.split("."))) for t in old_parts.tag.split("-"))
    new_parts = old_parts._replace(version=str(new_version), tag=new_tag)
    new_wheel_name = "-".join(p for p in new_parts if p) + ".whl"
    new_wheel = wheel.with_name(new_wheel_name)

    if not new_wheel.exists():
        raise RuntimeError(
            f"Failed to create new wheel {new_wheel}\n"
            f"Directory contents: {list(wheel.parent.iterdir())}"
        )
    return new_wheel


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--local-version")
    parser.add_argument("--version")
    parser.add_argument("--delete-old-wheel", action="store_true")
    parser.add_argument("--allow-same-version", action="store_true")
    args = parser.parse_args()

    new_wheel = change_wheel_version(
        wheel=args.wheel,
        version=args.version,
        local_version=args.local_version,
        allow_same_version=args.allow_same_version,
    )
    print(new_wheel)
    if args.delete_old_wheel:
        args.wheel.unlink()


if __name__ == "__main__":
    main()
