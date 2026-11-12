# Bootyhole: personal Kasm Workspace Registry

Registry for Kasm Workspaces (schema 1.1, Kasm 1.19.x). Catalog URL to add in Kasm: `https://daledibbadel.github.io/booythole/`

## Published workspaces
Prebuilt entries are Kasm's own official images for the same distribution as an ISO in the owner's library. **None is built from, or equivalent to, the ISO** (shared host kernel; no installer, bootloader or live-boot behavior).

| Workspace | Image | Matches owner ISO | Notes |
|---|---|---|---|
| Debian 12 Bookworm (Bootyhole) | `kasmweb/debian-bookworm-desktop:1.19.0-rolling-weekly` | Debian 12 live (Cinnamon) | official Kasm image |
| Ubuntu 22.04 Jammy (Bootyhole) | `kasmweb/ubuntu-jammy-desktop:1.19.0-rolling-weekly` | Ubuntu 22.04.4 desktop | official Kasm image |
| Ubuntu 24.04 Noble (Bootyhole) | `kasmweb/ubuntu-noble-desktop:1.19.0-rolling-weekly` | Ubuntu 24.04.3 desktop | official Kasm image |
| Kali Linux rolling (Bootyhole) | `kasmweb/kali-rolling-desktop:1.19.0-rolling-weekly` | Kali 2024.1 live | rolling release, newer than the ISO |
| Fedora 42 desktop (Bootyhole) | `kasmweb/fedora-42-desktop:1.19.0-rolling-weekly` | Fedora Server 42 DVD | related desktop edition, not the Server ISO |
| Tails 7.16 container (UNOFFICIAL, adapted from the owner's ISO) | `ghcr.io/daledibbadel/tails-unofficial:0.12` (LOCAL image, preload required) | Tails 7.16 ISO | **Not Tails.** Unprivileged container of the Tails root filesystem with Tor-only egress enforced by a separate gateway; browser sandbox with its own user/mount/PID namespace under a scoped Docker runtime, optional private saved profile (Enabled/Disabled/Reset), in-session screen lock; requirement for full Tails-equivalent hardening stays OPEN (shared kernel, no memory wipe). See `recipes/tails-unofficial/README.md`. |
| Tor Browser (Bootyhole) | `kasmweb/tor-browser:1.19.0-rolling-weekly` | none | The Tor Browser. It is not Tails. Needs a bridge on networks that cannot reach Tor relays; connects automatically through the built-in obfs4 bridges when the server-side file mapping `user.js` (see `recipes/tor-browser-bridges/`) is applied. |

## In progress (not published)
Workspaces built from the owner's other ISO media (PeppermintOS, others) are unfinished (paused). Nothing is listed until a custom image has been built from its source, launched through Kasm and tested. A registry lists Docker images; it cannot boot ISO files, run Windows, or provide Tails' kernel-level protections.

## Build
`./build.sh` (Node 20; `(cd processing && npm ci)` and `(cd site && npm ci)` first) stops on the first failure: image-reference self-test, catalog build, site export, then `node processing/verify.js` (names, icons, `1.19.x` compatibility, pinned image references under an allowed namespace, no private addresses or credential words). GitHub Actions publishes `public/` to `gh-pages` on every push to branch `1.1`.

## Adding a workspace
Create `workspaces/<Name>/workspace.json` plus its icon, add the owner's image namespace to `processing/imageref.js` if needed, commit to `1.1`.
