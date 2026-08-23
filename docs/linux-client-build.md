# GoreeCloud Notify Linux Client Build Standard

## Purpose

Define the compatibility requirements for the future GoreeCloud Notify Linux desktop client package.

## Supported baseline

Linux desktop artifacts must be built against:

- Ubuntu 22.04 LTS build environment
- GLIBC 2.35 compatibility baseline
- amd64 architecture
- Debian package format (`.deb`)

## Release validation

Every desktop package must validate:

- application launch on the supported baseline;
- desktop entry registration;
- icon installation;
- dependency resolution;
- shared library GLIBC requirements;
- clean uninstall and reinstall behavior.

## Incompatible builds

Packages requiring newer system libraries than the supported baseline must not be released.

Examples:

- GLIBC 2.36+
- GLIBC 2.37
- GLIBC 2.38
- GLIBC 2.39

## Future clients

The same standard applies to:

- GoreeCloud Notify Linux client
- GoreeCloud Terminal
- GoreeCloud Browser
- GoreeCloud Calendar
- GoreeCloud Contacts
- GoreeCloud Manager

The build system should use a shared GoreeCloud Linux application packaging pipeline.
