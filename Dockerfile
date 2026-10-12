FROM node:22-bookworm AS ui
WORKDIR /build/apps/workbench
COPY apps/workbench/package*.json ./
RUN npm ci
COPY apps/workbench/ ./
RUN npm run build && npm run build:plugin

FROM python:3.12-slim-bookworm AS wheel
WORKDIR /build
COPY . .
COPY --from=ui /build/apps/workbench/dist ./apps/workbench/dist
COPY --from=ui /build/apps/workbench/dist-plugin ./apps/workbench/dist-plugin
ENV DRAWAI_PREBUILT_UI=1
RUN pip install --no-cache-dir build && python -m build --wheel --outdir /wheels

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 libreoffice-impress poppler-utils pandoc fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*
COPY --from=wheel /wheels /wheels
RUN for wheel in /wheels/*.whl; do pip install --no-cache-dir "$wheel[workbench,llm]"; done \
    && rm -rf /wheels
ENV DRAWAI_HOME=/data DRAWAI_WORKBENCH_CLOUD_MODE=1
RUN useradd --create-home --uid 10001 drawai && mkdir /data && chown drawai:drawai /data
USER drawai
VOLUME ["/data"]
EXPOSE 8890
ENTRYPOINT ["drawai"]
CMD ["workbench", "--host", "0.0.0.0", "--port", "8890"]
