#!/bin/bash
# UNOFFICIAL Tails 7.16 root-filesystem container, startup v0.7. Runs entirely as the session user (uid 1000).
# No Tor client runs in this container: Tor lives in the separate egress gateway (kbtails-tor-gw) on an internal network with no route out.
export DISPLAY=:1 XDG_RUNTIME_DIR=/tmp/xdg-run
# gnome-shell shows "Screen Lock disabled" once per home when it has no GDM lock screen; the real lock here is kb-lock (Lock Screen menu), so mark the notice as shown
mkdir -p "$HOME/.local/share/gnome-shell" && : > "$HOME/.local/share/gnome-shell/lock-warning-shown"
# Profile guard: exactly one session may hold a saved (persistent) profile. The lock is held (fd 9, inherited by every child) until the session ends.
rm -f /tmp/kb-profile-busy; exec 9>"$HOME/.kb-profile.lock"; flock -n 9 || : > /tmp/kb-profile-busy
mkdir -p -m 700 "$XDG_RUNTIME_DIR" /tmp/sysbus
dbus-daemon --nofork --config-file=/etc/kb/sysbus.conf > /tmp/sysbus.log 2>&1 &
export DBUS_SYSTEM_BUS_ADDRESS=unix:path=/tmp/sysbus/system_bus_socket
python3 /etc/kb/fwd.py "${KB_GATEWAY:-172.28.0.2}" > /tmp/fwd.log 2>&1 &
python3 -I /usr/local/bin/kb-torstatus > /tmp/torstatus.log 2>&1 &
exec dbus-run-session -- bash -c '/usr/local/bin/kb-profile-banner & exec gnome-shell --x11 --sm-disable'
