#!/bin/bash
# kbtails-ensure: make sure the Tails-only infrastructure on karen exists and runs (idempotent; safe to run any time, e.g. at boot and every 5 minutes):
#   networks kbtails_int/kbtails_eg, Tor gateway container kbtails-tor-gw, Kasm callback relay kbtails-kasm-relay, peer-isolation nft table.
# The containers also have restart=unless-stopped (Docker restarts them within ~1 s of a crash); this covers a missing/stopped container (e.g. after an image prune or manual stop).
# Config: /etc/kbtails-ensure.conf (KB_IMAGE=..., KB_STAGE=/opt/kbtails/stage). Never touches Kasm containers or desktop sessions.
set -u
[ -f /etc/kbtails-ensure.conf ] && . /etc/kbtails-ensure.conf
export KB_STAGE=${KB_STAGE:-/opt/kbtails/stage}; IMG=${KB_IMAGE:-ghcr.io/daledibbadel/tails-unofficial:0.8}
log() { logger -t kbtails-ensure "$*"; echo "$*"; }
docker image inspect "$IMG" >/dev/null 2>&1 || { log "image $IMG missing: cannot (re)create gateway/relay"; exit 1; }
state() { local o; if o=$(docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null); then echo "$o"; else echo absent; fi; }
s=$(state kbtails-tor-gw)
case "$s" in true) ;; false) log "gateway stopped: starting"; docker start kbtails-tor-gw >/dev/null ;; absent) log "gateway absent: creating"; bash /opt/kbtails/gw_up.sh kbtails-tor-gw 172.28.0.2 "$IMG" ;; esac
s=$(state kbtails-kasm-relay)
case "$s" in true) ;; false) log "relay stopped: starting"; docker start kbtails-kasm-relay >/dev/null ;; absent) log "relay absent: creating"; bash /opt/kbtails/relay_up.sh kbtails-kasm-relay 172.28.0.10 "$IMG" ;; esac
nft list table bridge kbtails_isolation >/dev/null 2>&1 || { log "isolation table missing: applying"; /usr/local/sbin/kbtails-isolation apply; }
