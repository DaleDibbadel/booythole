set -e
docker network inspect kbtails_int >/dev/null 2>&1 || docker network create --internal --subnet 172.28.0.0/24 --gateway 172.28.0.1 kbtails_int >/dev/null
docker network inspect kbtails_eg >/dev/null 2>&1 || docker network create --subnet 172.29.0.0/24 -o com.docker.network.bridge.name=br_kbtails_eg kbtails_eg >/dev/null
docker rm -f kbtails-tor-gw >/dev/null 2>&1 || true
mkdir -p /etc/kbtails; install -m 0644 /tmp/gw-torrc /etc/kbtails/gw-torrc
docker create --name kbtails-tor-gw --mount type=bind,src=/etc/kbtails/gw-torrc,dst=/etc/kbtails-gw-torrc,readonly --restart unless-stopped --network kbtails_eg --user 1000:1000 --entrypoint tor \
  --sysctl net.ipv4.ip_unprivileged_port_start=0 --sysctl net.ipv4.ip_forward=0 --cap-drop ALL --security-opt no-new-privileges --read-only --tmpfs /var/lib/kbtails-tor:uid=1000,gid=1000,mode=700 --tmpfs /tmp \
  ghcr.io/daledibbadel/tails-unofficial:0.3 -f /etc/kbtails-gw-torrc >/dev/null
docker network connect --ip 172.28.0.2 kbtails_int kbtails-tor-gw
docker start kbtails-tor-gw
sleep 45
docker logs --tail 6 kbtails-tor-gw 2>&1 | cut -c1-160
docker network inspect -f '{{.Name}} internal={{.Internal}}' kbtails_int kbtails_eg
