# Changelog

## [v0.6.0]
- Add a `--platform-tag` option to change the platform tag of a wheel

## [v0.5.0]
- Work around the fact `wheel unpack` does not preserve permissions
- Avoid defensive check trigged by `wheel pack` sorting tags when reconstructing the wheel

## [v0.4.0]
- Work around a bug in `setuptools` involving really long versions when parsing `METADATA` files

## [v0.3.0]
- Add `--allow-same-version` to allow building a wheel with the same version as the old one

## [v0.2.0]
- Print filename of new wheel, swallow logs from subprocesses
- Add `--delete-old-wheel` to delete the old wheel

## [v0.1.1]
- Require Python 3.9 or newer to avoid `shutil.move` issue

## [v0.1]
- Initial release (yanked)
