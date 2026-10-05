FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive DISPLAY=:99 QT_QPA_PLATFORM=xcb LIBGL_ALWAYS_SOFTWARE=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb x11vnc novnc websockify ca-certificates python3 procps \
    libgl1 libegl1 libgl1-mesa-dri libasound2t64 libpulse0 libfontconfig1 \
    libx11-6 libxcb1 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 \
    libxcb-image0 libxcb-render-util0 libxcb-randr0 libxcb-xinerama0 \
    libxkbcommon-x11-0 libxcomposite1 libxrandr2 libxrender1 libxi6 \
    libdbus-1-3 libnss3 libopengl0 libwayland-client0 libwayland-cursor0 \
    && rm -rf /var/lib/apt/lists/*
COPY pcsx2-v2.8.2.AppImage /opt/pcsx2.AppImage
RUN apt-get update && apt-get install -y --no-install-recommends squashfs-tools && rm -rf /var/lib/apt/lists/*
COPY extract_appimage.py /opt/extract_appimage.py
RUN python3 /opt/extract_appimage.py
RUN apt-get update && apt-get install -y --no-install-recommends openbox && rm -rf /var/lib/apt/lists/*
COPY start.sh /opt/start.sh
RUN chmod +x /opt/start.sh
EXPOSE 6080
ENTRYPOINT ["/opt/start.sh"]
