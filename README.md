# change_wheel_version

A script to change the version of a package inside a pre-existing wheel. This is useful for e.g.
adding a local version to a custom built wheel, without having to jury rig its build process. Note
that this only affects the packaging metadata, not any version numbers in code.
