# UNOFFICIAL PeppermintOS container for Kasm (from the owner's PeppermintOS-Debian-64.iso)

Built on the Kasm agent host (not downloadable; no ISO or squashfs is published here):
1. Read-only copy of `live/filesystem.squashfs` from the ISO (sha256 of the ISO f9031574138be959e1b67666d62bd0300bcf93cb1a99403761f581bfe0323ea1, squashfs 7e54524f6ff13ee648fd9073141d00fd0a7aa2a1fcc3c9104d381243b420da8b; no upstream checksum on record), `unsquashfs`, `tar | docker import` -> `kbpep-rootfs:1`.
2. `Dockerfile` here adds the KasmVNC / Kasm startup components taken from `kasmweb/core-debian-bookworm` (`kasm-files.tar`, `perl-core.tar`, `xtools.tar`, `kb/`) and the `kasm-user` account, tag `ghcr.io/daledibbadel/peppermintos-unofficial:0.1`.
3. Register as a Kasm workspace with Docker Registry left blank (local image).

Tested in a real Kasm session: Xfce (xfwm4, panel, desktop) under KasmVNC, not privileged, no extra capabilities, default session network: LAN and `karen` denied by the host policy, internet open, disposable home. Differences from the ISO: host kernel, no live-session services, no installer.
