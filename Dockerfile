# ──────────────────────────────────────────────────────────────────────────────
# SELinux Explorer – Dockerfile
#
# Builds a self-contained image with every runtime dependency:
#   • Python 3.12 + pip packages (requirements.txt)
#   • PyQt5 (GUI) + its native Qt/X11 libraries
#   • Graphviz (used by PlantUML for diagram rendering)
#   • Java 17 (required to run plantuml.jar)
#   • Xvfb + x11vnc (headless display so the Qt window can run without a
#     physical screen — optional, see USAGE below)
#
# USAGE
# ─────
# Build:
#   docker build -t selinux-explorer .
#
# Run with your local X11 socket (Linux host):
#   docker run --rm -it \
#     -e DISPLAY=$DISPLAY \
#     -v /tmp/.X11-unix:/tmp/.X11-unix \
#     -v $(pwd)/policy:/policy \
#     selinux-explorer
#
# Run headless (no local X server needed):
#   docker run --rm -it \
#     -v $(pwd)/policy:/policy \
#     selinux-explorer headless
#
# The container entrypoint handles both modes (see bottom of this file).
# ──────────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim

LABEL maintainer="SELinux Explorer"
LABEL description="SELinux policy analysis and visualization tool"

# ── System dependencies ────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Qt / PyQt5 native libraries
    libqt5widgets5 \
    libqt5gui5 \
    libqt5core5a \
    libqt5dbus5 \
    libqt5network5 \
    libgl1 \
    libglib2.0-0 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    # Graphviz (diagram rendering)
    graphviz \
    # Java 21 (runs plantuml.jar)
    openjdk-21-jre-headless \
    # Headless display support
    xvfb \
    x11vnc \
    # Git (for submodule checkout if needed)
    git \
    # Utilities
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ────────────────────────────────────────────────────────
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

# ── Application source ─────────────────────────────────────────────────────────
WORKDIR /app
COPY app/ /app/

# Ensure the PythonUtilityClasses submodule is present (copied from workspace).
# If the image is built from a fresh clone without submodules initialised,
# uncomment the next two lines instead of the COPY above:
#   RUN git submodule update --init --recursive
# (requires the full .git directory to be present in the build context)

# Output and reference directories expected by the application
RUN mkdir -p /app/out /app/ref

# ── Environment ────────────────────────────────────────────────────────────────
# Tell Qt to use the xcb (X11) platform plugin by default.
# When running headless (Xvfb) this is set to the virtual display.
ENV QT_QPA_PLATFORM=xcb
# Silence Qt's "cannot connect to X server" warning when Xvfb is not yet ready
ENV QT_LOGGING_RULES="*.warning=false"
# Java home (openjdk-21 on Debian)
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

# ── Entrypoint ─────────────────────────────────────────────────────────────────
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
# Default: launch the GUI
CMD ["gui"]
