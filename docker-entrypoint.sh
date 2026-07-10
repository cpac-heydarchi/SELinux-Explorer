#!/bin/bash
# docker-entrypoint.sh
# Handles two run modes:
#   gui      – forward to an existing X11 display (DISPLAY + XAUTHORITY must be set)
#   headless – start a virtual Xvfb display, then launch the GUI on it
#
# For X11 forwarding the host must first create a docker-compatible auth cookie:
#
#   XAUTH_DOCKER=/tmp/.docker.xauth
#   touch $XAUTH_DOCKER
#   xauth nlist $DISPLAY | sed -e 's/^..../ffff/' | xauth -f $XAUTH_DOCKER nmerge -
#
# Then pass it to the container:
#   docker run ... \
#     -e DISPLAY=$DISPLAY \
#     -e XAUTHORITY=/tmp/.Xauth \
#     -v /tmp/.X11-unix:/tmp/.X11-unix \
#     -v $XAUTH_DOCKER:/tmp/.Xauth:ro \
#     selinux-explorer
set -e

MODE="${1:-gui}"

case "$MODE" in
    headless)
        # Start a virtual framebuffer on display :99
        Xvfb :99 -screen 0 1280x960x24 &
        export DISPLAY=:99
        # Give Xvfb a moment to initialise
        sleep 1
        echo "[entrypoint] Running in headless mode on display $DISPLAY"
        exec python /app/main.py
        ;;
    gui)
        if [ -z "$DISPLAY" ]; then
            echo "[entrypoint] ERROR: DISPLAY is not set."
            echo "  Mount the host X socket and pass -e DISPLAY=\$DISPLAY, or use the 'headless' mode."
            exit 1
        fi
        echo "[entrypoint] Running GUI on display $DISPLAY"
        exec python /app/main.py
        ;;
    *)
        # Pass-through: allow running arbitrary commands inside the container,
        # e.g.  docker run selinux-explorer pytest app/test
        exec "$@"
        ;;
esac
