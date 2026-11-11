const { validImageRef } = require("./imageref");
const ok = ["kasmweb/tor-browser:1.19.0-rolling-weekly", "ghcr.io/daledibbadel/tails-unofficial-kasm:0.1.0", "daledibbadel/mint-kasm:1.19.0", "ghcr.io/daledibbadel/x@sha256:" + "a".repeat(64), "ghcr.io/daledibbadel/x:1.0@sha256:" + "b".repeat(64)];
const bad = ["kasmweb/tor-browser", "kasmweb/tor-browser:latest", "ubuntu:22.04", "evil.example/kasmweb/x:1", "ghcr.io/daledibbadel/x:", "ghcr.io/daledibbadel/x@sha256:abc", "kasmweb/Tor Browser:1", "kasmweb/x:1 ; rm", "ghcr.io/daledibbadel/UPPER:1", "", null, "ghcr.io/other/x:1", "kasmweb/tor-browser:1.0:2"];
let fails = 0;
for (const r of ok) if (!validImageRef(r)) { console.error("should accept:", r); fails++; }
for (const r of bad) if (validImageRef(r)) { console.error("should refuse:", r); fails++; }
if (fails) process.exit(1);
console.log(`imageref tests ok: ${ok.length} accepted, ${bad.length} refused`);
