# Bootyhole: Kasm Workspace Registry

A small Kasm Workspaces registry (schema 1.1, Kasm 1.19.x) with generic workspace definitions only.
Catalog URL to add in Kasm (Admin > Workspaces > Registry): `https://daledibbadel.github.io/booythole/`

| Workspace | Image (Docker Hub) | Notes |
|---|---|---|
| Tor Browser | `kasmweb/tor-browser:1.19.0-rolling-weekly` | The Tor Browser. It is not Tails. |
| Ubuntu Desktop | `kasmweb/ubuntu-jammy-desktop:1.19.0-rolling-weekly` | Ubuntu 22.04 desktop |
| FileZilla | `kasmweb/filezilla:1.19.0-rolling-weekly` | FTP/SFTP client |

A registry lists Docker images. It cannot boot ISO files, run Windows, or provide Tails (which needs its own kernel).

## Build
`./build.sh` (Node 20; `npm ci --prefix processing && npm ci --prefix site` first). It stops on the first failure and ends with
`node processing/verify.js`, which fails unless the catalog is complete (names, icons, `1.19.x` compatibility, no private addresses or credential words).
GitHub Actions (`.github/workflows/build-and-deploy.yml`) runs it on every push to branch `1.1` and publishes `public/` to `gh-pages`.

## Adding a workspace
Create `workspaces/<Name>/workspace.json` plus its icon (schema in `workspaces/README.md`), commit to `1.1`.
