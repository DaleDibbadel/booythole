FROM ghcr.io/daledibbadel/tails-unofficial:0.4
USER root
# Tails removes X11 from the Tor Browser flatpak (Wayland-only GNOME). Kasm's KasmVNC desktop is X11-only, so grant the X11 socket (documented difference)
RUN sed -i 's/^sockets=!x11;!fallback-x11;cups/sockets=x11;cups/' /var/lib/flatpak/overrides/org.boum.tails.TorBrowser
COPY sbx_test.sh /usr/local/bin/kb-sbx-test
COPY fwd.py kbctl.py /etc/kb/
COPY kb-torstatus kb-tor-browser kb-bwrap kb-onioncircuits kb-tca /usr/local/bin/
COPY custom_startup.sh /dockerstartup/custom_startup.sh
COPY gateway/kbgw.py gateway/torrc gateway/deny.conf /etc/kbgw-default/
# /run/tor-has-bootstrapped is the readiness file Tails' GNOME Tor-status extension and Tor Browser read; kb-torstatus keeps it truthful
RUN mkdir -p /run/tor-has-bootstrapped && chown 1000:1000 /run/tor-has-bootstrapped \
 && chmod 755 /usr/local/bin/kb-* /dockerstartup/custom_startup.sh && chown 1000:1000 /dockerstartup/custom_startup.sh \
 && ln -sf /usr/local/bin/kb-tor-browser /usr/local/lib/launch-tor-browser \
 && ln -sf /usr/local/bin/kb-onioncircuits /usr/local/bin/onioncircuits \
 && sed -i 's#^Exec=/bin/systemctl --user start tca#Exec=/usr/local/bin/kb-tca#' /usr/share/applications/tca.desktop && grep -n '^Exec=' /usr/share/applications/tca.desktop
# GNOME screen lock needs a local login (GDM) that does not exist here: the lock UI only produced a misleading 'Screen Lock disabled' notice. The session is
# protected by Kasm's own authentication (login, per-session token, idle disconnect, session time limit); do not offer a lock screen that cannot work.
RUN printf '[org/gnome/desktop/screensaver]\nlock-enabled=false\nidle-activation-enabled=false\n\n[org/gnome/desktop/lockdown]\ndisable-lock-screen=true\n\n[org/gnome/desktop/session]\nidle-delay=uint32 0\n' > /etc/dconf/db/local.d/99_kb-session && dconf update && rm -f /usr/share/glib-2.0/schemas/90_kb-session.gschema.override
ENV KB_TAILS_RUNTIME=1 KB_RELAY=172.28.0.10:443
# v0.5: (1) Kasm session callbacks go to the Tails-only relay (kbtails-kasm-relay), over /usr/bin/curl: Tails' /usr/local/bin/curl wrapper forces every curl through
# Tor, which refused the internal callback address, so status/log callbacks never reached Kasm. (2) real screen lock (kb-lock) behind Tails' own menu entry.
RUN for f in /dockerstartup/vnc_startup.sh /dockerstartup/kasm_end_session_recoverable.sh /dockerstartup/kasm_pre_shutdown_user.sh; do \
      sed -i '/\/api\//{s# curl # /usr/bin/curl #; s#https://${KASM_API_HOST}:${KASM_API_PORT}/api/#https://${KB_RELAY}/api/#g}' "$f"; done \
 && ! grep -rn 'KASM_API_HOST}:${KASM_API_PORT}/api' /dockerstartup \
 && grep -c 'KB_RELAY' /dockerstartup/vnc_startup.sh
COPY kb-lock kb-profile-banner /usr/local/bin/
RUN chmod 755 /usr/local/bin/kb-lock /usr/local/bin/kb-profile-banner && printf '\n[org/gnome/desktop/privacy]\nusb-protection=false\n' >> /etc/dconf/db/local.d/99_kb-session && dconf update && ln -sf /usr/local/bin/kb-lock /usr/local/bin/tails-screen-locker
LABEL org.opencontainers.image.title="UNOFFICIAL container adapted from the owner's Tails 7.16 ISO (experimental, not Tails)"
USER 1000
