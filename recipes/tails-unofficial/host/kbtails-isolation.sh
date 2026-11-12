#!/bin/bash
# kbtails-isolation: peer isolation for the UNOFFICIAL Tails workspace network (kbtails_int) on karen. Idempotent. Usage: kbtails-isolation {apply|remove|status}
# Docker bridges forward same-bridge traffic at layer 2 (no br_netfilter here), so the iptables session policy never saw desktop->desktop or
# desktop->kasm_proxy traffic. This nftables *bridge-family* table closes that: inside the kbtails_int bridge only
#   * replies to connections that were allowed (conntrack),
#   * any desktop -> the Tor gateway (the only service a desktop may initiate to), and
#   * kasm_proxy -> desktops (Kasm's streaming path, which Kasm attaches to the network),
# are forwarded; everything else (desktop<->desktop, desktop->kasm_proxy, IPv6, other ethertypes) is dropped. ARP stays allowed.
set -u
NET=kbtails_int
CONF=/etc/kbtails-isolation.conf
GW_IPS="172.28.0.2"; [ -f "$CONF" ] && . "$CONF"
br=$(docker network inspect $NET -f '{{or (index .Options "com.docker.network.bridge.name") (printf "br-%.12s" .Id)}}' 2>/dev/null)
apply() {
  [ -n "$br" ] || { logger -t kbtails-isolation "network $NET absent; nothing to do"; return 0; }
  proxy=$(docker network inspect $NET -f '{{range .Containers}}{{if eq .Name "kasm_proxy"}}{{.IPv4Address}}{{end}}{{end}}' 2>/dev/null | cut -d/ -f1)
  gws=$(echo $GW_IPS | tr ' ' ',')
  f=$(mktemp)
  {
    echo "table bridge kbtails_isolation"; echo "delete table bridge kbtails_isolation"
    echo "table bridge kbtails_isolation {"
    echo "  chain peer { type filter hook forward priority -150; policy accept;"
    echo "    meta ibrname != \"$br\" accept"
    echo "    ether type arp accept"
    echo "    ct state established,related accept"
    echo "    ip daddr { $gws } accept comment \"desktops -> Tor gateway\""
    [ -n "$proxy" ] && echo "    ip saddr $proxy accept comment \"kasm_proxy -> desktops (streaming)\""
    echo "    counter drop comment \"peer isolation: everything else inside kbtails_int\""
    echo "  }"
    echo "}"
  } > "$f"
  nft -f "$f" && logger -t kbtails-isolation "applied on $br gateways=[$gws] proxy=[${proxy:-none}]"; rc=$?
  rm -f "$f"; return $rc
}
case "${1:-}" in apply) apply;; remove) nft delete table bridge kbtails_isolation 2>/dev/null; echo removed;; status) nft list table bridge kbtails_isolation;; *) echo "usage: $0 apply|remove|status"; exit 2;; esac
