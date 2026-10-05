#!/bin/sh
set -eu
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
Xvfb :99 -screen 0 1024x768x24 -nolisten tcp > /data/xvfb.log 2>&1 &
for task_attempt in 1 2 3 4 5; do
  test -S /tmp/.X11-unix/X99 && break
  sleep 1
done
openbox > /data/openbox.log 2>&1 &
x11vnc -display :99 -localhost -forever -shared -nopw -rfbport 5900 > /data/vnc.log 2>&1 &
websockify --web=/usr/share/novnc 6080 localhost:5900 > /data/websockify.log 2>&1 &
if test -r /data/boot-state-path.txt; then
  task_boot_state=$(cat /data/boot-state-path.txt)
  case "$task_boot_state" in /data/sstates/*.p2s) ;; *) exit 1 ;; esac
  test -f "$task_boot_state"
  set -- -statefile "$task_boot_state" /game.bin
fi
exec /opt/squashfs-root/AppRun -nogui -datapath /data "$@" > /data/pcsx2.log 2>&1
