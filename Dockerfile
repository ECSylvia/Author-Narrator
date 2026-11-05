FROM python:3.13-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends espeak-ng \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir /data && chown 10001:10001 /data
WORKDIR /app
COPY local_web.py ./
COPY src/core/manuscript_parser.py ./src/core/
COPY web ./web
ENV NARRATOR_BIND=0.0.0.0 NARRATOR_DATA_DIR=/data PYTHONUNBUFFERED=1
USER 10001:10001
EXPOSE 8765
CMD ["python", "local_web.py"]
