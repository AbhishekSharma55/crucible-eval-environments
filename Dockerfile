FROM python@sha256:8fb099199b9f2d70342674bd9dbccd3ed03a258f26bbd1d556822c6dfc60c317

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates=20250419~deb12u1 \
        git=1:2.39.5-0+deb12u3 \
        less=590-2.1~deb12u2 \
    && rm -rf /var/lib/apt/lists/* \
    && ! command -v cc \
    && ! command -v gcc

WORKDIR /opt/crucible
COPY config/repos.json config/repos.json
COPY config/locks config/locks
COPY sandbox sandbox
RUN python sandbox/setup_image.py \
    && rm -rf /opt/setup-checkouts /root/.cache

ENTRYPOINT ["python", "/opt/crucible/sandbox/entrypoint.py"]
