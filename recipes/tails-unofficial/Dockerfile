FROM kbtails-proto:0.1
USER root
# Tails removes X11 from the Tor Browser flatpak (Wayland-only GNOME). Kasm's KasmVNC desktop is X11-only, so grant the X11 socket (documented difference)
RUN sed -i 's/^sockets=!x11;!fallback-x11;cups/sockets=x11;cups/' /var/lib/flatpak/overrides/org.boum.tails.TorBrowser && grep -n '^sockets=' /var/lib/flatpak/overrides/org.boum.tails.TorBrowser
COPY fwd.py /etc/kb/fwd.py
COPY kb-tor-browser /usr/local/bin/kb-tor-browser
COPY kb-bwrap /usr/local/bin/kb-bwrap
COPY custom_startup.sh /dockerstartup/custom_startup.sh
RUN chmod 755 /usr/local/bin/kb-tor-browser /usr/local/bin/kb-bwrap /dockerstartup/custom_startup.sh && chown 1000:1000 /dockerstartup/custom_startup.sh
# Tails' own launcher needs sudo, a network namespace (tbb), onion-grater and systemd; replace its last step with the unprivileged wrapper so the dock/menu Tor Browser entries work
RUN ln -sf /usr/local/bin/kb-tor-browser /usr/local/lib/launch-tor-browser
LABEL org.opencontainers.image.title="UNOFFICIAL container adapted from the owner's Tails 7.16 ISO (experimental, not Tails)"
USER 1000
