# kbtails Kasm callback relay launcher (UNOFFICIAL). Usage: relay_up.sh <name> <internal-ip> <image> (root on karen; kbrelay.py staged in ${KB_STAGE:-/tmp/kbgw-stage})
set -e
NAME=${1:-kbtails-kasm-relay}; IP=${2:-172.28.0.10}; IMG=${3:-ghcr.io/daledibbadel/tails-unofficial:0.4}
docker rm -f "$NAME" >/dev/null 2>&1 || true
mkdir -p /etc/kbrelay; install -m 0644 ${KB_STAGE:-/tmp/kbgw-stage}/kbrelay.py /etc/kbrelay/kbrelay.py
docker create --name "$NAME" --restart unless-stopped --network kasm_default_network --user 1000:1000 --entrypoint /usr/bin/python3 \
  --mount type=bind,src=/etc/kbrelay,dst=/etc/kbrelay,readonly -e KB_LISTEN="$IP" \
  --sysctl net.ipv4.ip_unprivileged_port_start=0 --cap-drop ALL --security-opt no-new-privileges --read-only --tmpfs /tmp:uid=1000,gid=1000 \
  "$IMG" -I /etc/kbrelay/kbrelay.py >/dev/null
docker network connect --ip "$IP" kbtails_int "$NAME"
docker start "$NAME" >/dev/null
