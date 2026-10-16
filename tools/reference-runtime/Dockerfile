# Build base first with tools/headless-runtime/Dockerfile (pinned AppImage).
FROM carmodels-mc3-gs-reference:2.8.2
RUN apt-get update && apt-get install -y --no-install-recommends g++ && rm -rf /var/lib/apt/lists/*
