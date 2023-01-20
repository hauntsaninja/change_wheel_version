import argparse
import email.parser
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

import installer.utils
import packaging.version


def version_replace(v: packaging.version.Version, **kwargs: Any) -> packaging.version.Version:
    # yikes :-)
    self = packaging.version.Version.__new__(packaging.version.Version)
    self._version = v._version._replace(**kwargs)
    return packaging.version.Version(str(self))


def change_wheel_version(wheel: Path, version: Optional[str], local_version: Optional[str]) -> Path:
    old_parts = installer.utils.parse_wheel_filename(wheel.name)
    old_version = packaging.version.Version(old_parts.version)
    distribution = old_parts.distribution

    if version is None:
        assert local_version is not None
        new_version = version_replace(
            old_version, local=packaging.version._parse_local_version(local_version)
        )
    else:
        new_version = packaging.version.Version(version)
        assert not new_version.local
        if local_version:
            new_version = version_replace(
                new_version, local=packaging.version._parse_local_version(local_version)
            )

    assert new_version != old_version

    new_parts = old_parts._replace(version=str(new_version))
    new_wheel_name = "-".join(p for p in new_parts if p) + ".whl"
    new_wheel = wheel.with_name(new_wheel_name)

    with tempfile.TemporaryDirectory() as _tmpdir:
        tmpdir = Path(_tmpdir)
        dest_dir = tmpdir / "wheel"

        subprocess.check_output(
            [sys.executable, "-m", "wheel", "unpack", "-d", str(dest_dir), str(wheel)]
        )

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
        with open(metadata, "rb") as f:
            parser = email.parser.BytesParser()
            msg = parser.parse(f)
        msg.replace_header("Version", str(new_version))
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

    assert new_wheel.exists()
    return new_wheel


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--local-version")
    parser.add_argument("--version")
    parser.add_argument("--delete-old-wheel", action="store_true")
    args = parser.parse_args()

    new_wheel = change_wheel_version(args.wheel, args.version, args.local_version)
    print(new_wheel)
    if args.delete_old_wheel:
        args.wheel.unlink()


if __name__ == "__main__":
    main()
