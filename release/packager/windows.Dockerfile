# Local build/test helper only. End users run fusion-pack.exe without Docker.
FROM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2
RUN apt-get update && apt-get install -y --no-install-recommends \
    wine64 unzip xvfb xauth ca-certificates && rm -rf /var/lib/apt/lists/*
ENV WINEDEBUG=-all WINEARCH=win64 WINEPREFIX=/wine
ENV WINEDLLOVERRIDES="mscoree,mshtml="
COPY python.3.13.7.nupkg /tmp/python.nupkg
RUN unzip -q /tmp/python.nupkg -d /python && rm /tmp/python.nupkg
# Build dependencies are installed offline in the developer container.
COPY wheels /wheels
RUN xvfb-run -a /usr/lib/wine/wine64 /python/tools/python.exe -m pip install \
    --no-index --find-links=Z:/wheels pyinstaller==6.22.3 \
    pyinstaller-hooks-contrib==2026.10 altgraph==0.17.5 packaging==26.3 \
    setuptools==84.2.1 pefile==2024.8.26 pywin32-ctypes==0.2.3
ENV LANG=C.UTF-8
WORKDIR /project
