# kbtails Tor egress gateway v2 (UNOFFICIAL). Usage: gw_up.sh <name> <internal-ip> <image>  (run as root on karen; files staged in /tmp/kbgw-stage)
set -e
NAME=${1:-kbtails-tor-gw}; IP=${2:-172.28.0.2}; IMG=${3:-ghcr.io/daledibbadel/tails-unofficial:0.4}
docker network inspect kbtails_int >/dev/null 2>&1 || docker network create --internal --subnet 172.28.0.0/24 --gateway 172.28.0.1 kbtails_int >/dev/null
docker network inspect kbtails_eg >/dev/null 2>&1 || docker network create --subnet 172.29.0.0/24 -o com.docker.network.bridge.name=br_kbtails_eg kbtails_eg >/dev/null
docker rm -f "$NAME" >/dev/null 2>&1 || true
mkdir -p /etc/kbgw; install -m 0644 /tmp/kbgw-stage/torrc /etc/kbgw/torrc; install -m 0644 /tmp/kbgw-stage/deny.conf /etc/kbgw/deny.conf; install -m 0644 /tmp/kbgw-stage/kbgw.py /etc/kbgw/kbgw.py
docker create --name "$NAME" --restart unless-stopped --network kbtails_eg --user 1000:1000 --entrypoint /usr/bin/python3 \
  --mount type=bind,src=/etc/kbgw,dst=/etc/kbgw,readonly -e KB_LISTEN="$IP" -e KB_DEBUG="${KB_DEBUG:-}" \
  --sysctl net.ipv4.ip_unprivileged_port_start=0 --sysctl net.ipv4.ip_forward=0 --cap-drop ALL --security-opt no-new-privileges --read-only \
  --tmpfs /var/lib/kbtails-tor:uid=1000,gid=1000,mode=700 --tmpfs /tmp:uid=1000,gid=1000 \
  "$IMG" -I /etc/kbgw/kbgw.py >/dev/null
docker network connect --ip "$IP" kbtails_int "$NAME"
docker start "$NAME" >/dev/null
