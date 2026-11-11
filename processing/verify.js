// Fails (exit 1) unless the built catalog is complete and sane. Usage: node processing/verify.js <publicDir> <schema>
const fs = require("fs"), path = require("path");
const [pub, schema] = process.argv.slice(2);
const fail = (m) => { console.error("VERIFY FAILED: " + m); process.exit(1); };
const list = path.join(pub, schema, "list.json");
if (!fs.existsSync(list)) fail("missing " + list);
const j = JSON.parse(fs.readFileSync(list, "utf8"));
const dirs = fs.readdirSync("workspaces", { withFileTypes: true }).filter(d => d.isDirectory() && fs.existsSync(path.join("workspaces", d.name, "workspace.json")));
if (j.name !== "Bootyhole") fail("registry name is " + j.name);
if (j.workspacecount !== dirs.length || j.workspaces.length !== dirs.length) fail(`catalog has ${j.workspaces.length} workspaces, folders have ${dirs.length}`);
if (j.list_url !== "https://daledibbadel.github.io/booythole/") fail("list_url " + j.list_url);
for (const w of j.workspaces) {
  if (!w.friendly_name || !w.description || !w.image_src) fail("incomplete entry " + JSON.stringify(w.friendly_name));
  if (!fs.existsSync(path.join(pub, schema, "icons", w.image_src))) fail("missing icon " + w.image_src);
  if (!(w.compatibility || []).some(c => c.version === "1.19.x" && /^kasmweb\/[a-z0-9-]+:[A-Za-z0-9._-]+$/.test(c.image))) fail("no 1.19.x compatibility with a kasmweb image in " + w.friendly_name);
  if (/TornBrowser|\bTails\b/i.test(w.friendly_name) && /tor/i.test(w.friendly_name)) fail("Tor entry must not be named Tails: " + w.friendly_name);
}
const text = fs.readFileSync(list, "utf8");
if (/\b(10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)\b/.test(text)) fail("private address in catalog");
if (/(token|secret|password)/i.test(text)) fail("credential-like word in catalog");
if (!fs.existsSync(path.join(pub, "index.html")) || !fs.existsSync(path.join(pub, schema, "index.html"))) fail("missing index.html");
console.log(`verify ok: ${j.workspaces.length} workspaces, channels ${JSON.stringify(j.channels)}, default ${j.default_channel}`);
