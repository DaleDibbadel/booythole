# Bootyhole: personal Kasm Workspace Registry

Registry for Kasm Workspaces (schema 1.1, Kasm 1.19.x). Catalog URL to add in Kasm: `https://daledibbadel.github.io/booythole/`

## Published workspaces
| Workspace | Image | Notes |
|---|---|---|
| Tor Browser (Bootyhole) | `kasmweb/tor-browser:1.19.0-rolling-weekly` | The Tor Browser. It is not Tails. |

## In progress (not published)
Workspaces built from the owner's own ISO media (Tails first, then other Linux media) are unfinished experiments. Nothing is listed until a custom image has been built from its source, launched through Kasm and tested. A registry lists Docker images; it cannot boot ISO files, run Windows, or provide Tails' kernel-level protections.

## Build
`./build.sh` (Node 20; `(cd processing && npm ci)` and `(cd site && npm ci)` first) stops on the first failure: image-reference self-test, catalog build, site export, then `node processing/verify.js` (names, icons, `1.19.x` compatibility, pinned image references under an allowed namespace, no private addresses or credential words). GitHub Actions publishes `public/` to `gh-pages` on every push to branch `1.1`.

## Adding a workspace
Create `workspaces/<Name>/workspace.json` plus its icon, add the owner's image namespace to `processing/imageref.js` if needed, commit to `1.1`.
