#!/bin/bash
# Runtime check of the EFFECTIVE Tor Browser sandbox (run inside the desktop container as the session user): what the process inside bubblewrap/flatpak really has.
export FLATPAK_FANCY_OUTPUT=0 XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/tmp/xdg-run} FLATPAK_BWRAP=/usr/local/bin/kb-bwrap
RT=/var/lib/flatpak-tails/runtime/org.boum.tails.Platform/x86_64/stable/active/files
echo "== container (outside sandbox)"; for n in pid user mnt net ipc; do echo "$n $(readlink /proc/self/ns/$n)"; done; grep -E "^(Seccomp|NoNewPrivs|CapEff|CapBnd)" /proc/self/status; cat /proc/self/attr/current 2>/dev/null
echo "== inside flatpak/bwrap sandbox"
bwrap --dev-bind / / --bind /usr "$RT" -- flatpak --installation=tails run --command=sh org.boum.tails.TorBrowser -c '
for n in pid user mnt net ipc; do echo "$n $(readlink /proc/self/ns/$n)"; done
grep -E "^(Seccomp|NoNewPrivs|CapEff|CapBnd|Uid)" /proc/self/status
echo "attr: $(cat /proc/self/attr/current 2>&1)"
echo "unshare -U: $(unshare -U true 2>&1 && echo ALLOWED || echo blocked)"
echo "unshare -m: $(unshare -m true 2>&1 && echo ALLOWED || echo blocked)"
echo "data: $(ls /data 2>&1 | head -2)  share: $(ls /share 2>&1 | head -2)"
echo "home listing: $(ls ~ 2>&1 | tr "\n" " ")"
echo "visible pids: $(ls /proc | grep -c "^[0-9]")  pid1: $(tr "\0" " " </proc/1/cmdline | cut -c1-60)"
echo "ptrace self-test: $(python3 - <<PY 2>&1
import ctypes
l=ctypes.CDLL(None,use_errno=True); r=l.ptrace(0,0,0,0); print("rc",r,"errno",ctypes.get_errno())
PY
)"
echo "net: $(timeout 4 curl -s -m 3 https://1.1.1.1 >/dev/null 2>&1 && echo DIRECT-OK || echo direct-blocked)"
'
