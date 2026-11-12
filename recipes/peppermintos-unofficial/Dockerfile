FROM kbpep-rootfs:1
USER root
ADD kasm-files.tar /
ENV AUDIO_PORT="4901"
ENV DEBIAN_FRONTEND="noninteractive"
ENV DISPLAY=":1"
ENV DISTRO="debian"
ENV GOMP_SPINCOUNT="0"
ENV INST_SCRIPTS="/dockerstartup/install"
ENV KASMVNC_AUTO_RECOVER="true"
ENV KASM_VNC_PATH="/usr/share/kasmvnc"
ENV LANG="en_US.UTF-8"
ENV LANGUAGE="en_US:en"
ENV LC_ALL="en_US.UTF-8"
ENV LD_LIBRARY_PATH="/opt/libjpeg-turbo/lib64/:/usr/local/lib/:/usr/lib/x86_64-linux-gnu:/usr/lib/i386-linux-gnu:/usr/local/nvidia/lib:/usr/local/nvidia/lib64"
ENV MAX_FRAME_RATE="24"
ENV NO_VNC_PORT="6901"
ENV OMP_WAIT_POLICY="PASSIVE"
ENV PULSE_RUNTIME_PATH="/var/run/pulse"
ENV SDL_GAMECONTROLLERCONFIG="030000005e040000be02000014010000,XInput Controller,platform:Linux,a:b0,b:b1,x:b2,y:b3,back:b8,guide:b16,start:b9,leftstick:b10,rightstick:b11,leftshoulder:b4,rightshoulder:b5,dpup:b12,dpdown:b13,dpleft:b14,dpright:b15,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:b6,righttrigger:b7"
ENV SHELL="/bin/bash"
ENV START_PULSEAUDIO="1"
ENV STARTUPDIR="/dockerstartup"
ENV START_XFCE4="1"
ENV TERM="xterm"
ENV VNC_COL_DEPTH="24"
ENV VNCOPTIONS="-PreferBandwidth -DynamicQualityMin=4 -DynamicQualityMax=7 -DLP_ClipDelay=0"
ENV VNC_PORT="5901"
ENV VNC_RESOLUTION="1280x720"
ENV VNC_VIEW_ONLY_PW="vncviewonlypassword"
ENV TZ="Etc/UTC"
RUN groupadd -g 1000 kasm-user && useradd -m -u 1000 -g 1000 -G audio,video -s /bin/bash kasm-user && cp -rT /home/kasm-default-profile /home/kasm-user 2>/dev/null; chown -R 1000:1000 /home/kasm-user; ln -sf /usr/bin/Xkasmvnc /usr/bin/Xvnc; ln -sf /usr/bin/kasmvncserver /usr/bin/vncserver; ln -sf /usr/bin/kasmvncpasswd /usr/bin/vncpasswd
ADD perl-core.tar /tmp/pc/
RUN cp -rn /tmp/pc/usr/. /usr/ && rm -rf /tmp/pc
ADD xtools.tar /
COPY kb/ /etc/kb/
ENV START_PULSEAUDIO="0"
RUN dbus-uuidgen > /etc/machine-id && mkdir -p /var/lib/dbus && ln -sf /etc/machine-id /var/lib/dbus/machine-id
COPY custom_startup.sh /dockerstartup/custom_startup.sh
RUN chmod +x /dockerstartup/custom_startup.sh && chown -R 1000:1000 /dockerstartup
LABEL org.opencontainers.image.title="UNOFFICIAL PeppermintOS (Debian) root filesystem prototype for Kasm (not the Peppermint ISO)"
USER 1000
ENTRYPOINT ["/dockerstartup/kasm_default_profile.sh","/dockerstartup/vnc_startup.sh","/dockerstartup/kasm_startup.sh"]
CMD ["--wait"]
