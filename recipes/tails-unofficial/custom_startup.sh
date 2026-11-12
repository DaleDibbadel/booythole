#!/bin/bash
# UNOFFICIAL Tails 7.16 root-filesystem container, startup v0.4. Runs entirely as the session user (uid 1000).
# No Tor client runs in this container: Tor lives in the separate egress gateway (kbtails-tor-gw) on an internal network with no route out.
export DISPLAY=:1 XDG_RUNTIME_DIR=/tmp/xdg-run
mkdir -p -m 700 "$XDG_RUNTIME_DIR" /tmp/sysbus
dbus-daemon --nofork --config-file=/etc/kb/sysbus.conf > /tmp/sysbus.log 2>&1 &
export DBUS_SYSTEM_BUS_ADDRESS=unix:path=/tmp/sysbus/system_bus_socket
python3 /etc/kb/fwd.py "${KB_GATEWAY:-172.28.0.2}" > /tmp/fwd.log 2>&1 &
python3 -I /usr/local/bin/kb-torstatus > /tmp/torstatus.log 2>&1 &
exec dbus-run-session -- gnome-shell --x11 --sm-disable
