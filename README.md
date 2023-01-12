# change_wheel_version

A script to change the version of a package inside a pre-existing wheel.

This is useful for e.g. adding a local version to a custom built wheel, without having to jury rig
its build process:

```bash
pipx run change_wheel_version some.whl --local-version special.build.info
```

Note that this only affects the packaging metadata, not any version numbers in code.
