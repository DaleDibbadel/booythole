// Docker image reference validation for registry entries. A reference must be pinned (explicit tag other than "latest", or an @sha256 digest)
// and live under an allowed namespace/registry. Add the owner's namespace to ALLOWED when the first custom image is published.
const ALLOWED = ["kasmweb/", "ghcr.io/daledibbadel/", "daledibbadel/"];
const NAME = "[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*";
const HOST = "[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?(?::[0-9]+)?";
const RE = new RegExp(`^(?:${HOST}/)?(?:${NAME}/)*${NAME}(?::([A-Za-z0-9_][A-Za-z0-9._-]{0,127}))?(?:@(sha256:[a-f0-9]{64}))?$`);
function validImageRef(ref) {
  if (typeof ref !== "string" || ref.length > 255 || /\s/.test(ref)) return false;
  const m = RE.exec(ref);
  if (!m) return false;
  const tag = m[1], digest = m[2];
  if (!digest && (!tag || tag === "latest")) return false;           // pinned only
  return ALLOWED.some((p) => ref.startsWith(p));
}
module.exports = { validImageRef, ALLOWED };
