ARG PYTHON_BUILDER_IMAGE=3.11-slim-bullseye
ARG PYTHON_RUN_IMAGE=gcr.io/distroless/cc:nonroot

## ---------------------------------------------------------------------------------- ##
## ------------------------- Python base -------------------------------------------- ##
## ---------------------------------------------------------------------------------- ##
FROM python:${PYTHON_BUILDER_IMAGE} as python-base
ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8
WORKDIR /workspace/app

## -------------------------- add common compiled libraries --------------------------- ##
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libsqlite3-dev \
        liblzma5 \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /root/.cache \
    && rm -rf /var/apt/lists/* \
    && rm -rf /var/cache/apt/* \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false
RUN pip install --upgrade pip wheel setuptools cython virtualenv
RUN mkdir -p /workspace/app \
    && addgroup --system --gid 65532 nonroot \
    && adduser --no-create-home --system --uid 65532 nonroot \
    && chown -R nonroot:nonroot /workspace

## ---------------------------------------------------------------------------------- ##
## ------------------------- Python build base -------------------------------------- ##
## ---------------------------------------------------------------------------------- ##
FROM python-base AS build-image
ARG POETRY_INSTALL_ARGS="--only main"
ENV POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_ALWAYS_COPY=1 \
    POETRY_CACHE_DIR='/var/cache/pypoetry' \
    POETRY_VERSION='1.4.2' \
    POETRY_INSTALL_ARGS="${POETRY_INSTALL_ARGS}" \
    GRPC_PYTHON_BUILD_WITH_CYTHON=1 \
    PATH="/workspace/app/.venv/bin:/usr/local/bin:$PATH"
## -------------------------- add development packages ------------------------------ ##
RUN apt-get install -y --no-install-recommends curl \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /root/.cache \
    && rm -rf /var/apt/lists/* \
    && rm -rf /var/cache/apt/* \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false

## -------------------------- install application ----------------------------------- ##
WORKDIR /workspace/app
RUN curl -sSL https://install.python-poetry.org | python - \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry
COPY --chown=65532:65532 \
    pyproject.toml \
    poetry.lock \
    README.md \
    alembic.ini \
    ./
RUN python -m venv --copies /workspace/app/.venv
RUN . /workspace/app/.venv/bin/activate \
    && pip install -U cython \
    && poetry install $POETRY_INSTALL_ARGS --no-root
COPY --chown=65532:65532 src ./src
RUN chown -R 65532:65532 /workspace && . /workspace/app/.venv/bin/activate && poetry install $POETRY_INSTALL_ARGS
EXPOSE 8000


## ---------------------------------------------------------------------------------- ##
## ------------------------- distroless runtime build ------------------------------- ##
## ---------------------------------------------------------------------------------- ##
## ------------------------- use distroless `cc` image  ----------------------------- ##

FROM ${PYTHON_RUN_IMAGE} as run-image
# persistent env values:
# ARG ENV_SECRETS="runtime-secrets"
ARG ARCHPREFIX
ENV PATH="/workspace/app/.venv/bin:$PATH" \
    # ENV_SECRETS="${ENV_SECRETS}" \
    CHIPSET_ARCH="${ARCHPREFIX}-linux-gnu"

## ------------------------- copy python itself from builder -------------------------- ##
COPY --from=python-base /usr/local/lib/ /usr/local/lib/
COPY --from=python-base /usr/local/bin/python /usr/local/bin/python
COPY --from=python-base /etc/ld.so.cache /etc/ld.so.cache

## -------------------------- add common compiled libraries --------------------------- ##
# If seeing ImportErrors, check if in the python-base already and copy as below
# required by lots of packages - e.g. six, numpy, wsgi
COPY --from=python-base /lib/${CHIPSET_ARCH}/libz.so.1 /lib/${CHIPSET_ARCH}/
COPY --from=python-base /lib/${CHIPSET_ARCH}/libbz2.so.1.0 /lib/${CHIPSET_ARCH}/
COPY --from=python-base /usr/lib/${CHIPSET_ARCH}/libffi* /usr/lib/${CHIPSET_ARCH}/
COPY --from=python-base /lib/${CHIPSET_ARCH}/libexpat* /lib/${CHIPSET_ARCH}/
# required by twentyqs
COPY --from=python-base /usr/lib/${CHIPSET_ARCH}/libsqlite3.so.0 /lib/${CHIPSET_ARCH}/
COPY --from=python-base /lib/${CHIPSET_ARCH}/liblzma.so.5 /lib/${CHIPSET_ARCH}/

## -------------------------- add application ---------------------------------------- ##
COPY --from=build-image --chown=65532:65532 /workspace/app/.venv  /workspace/app/.venv
COPY --from=build-image --chown=65532:65532 /workspace/app/src /workspace/app/src
COPY --from=build-image --chown=65532:65532 /workspace/app/alembic.ini  /workspace/app/alembic.ini

## --------------------------- standardize execution env ----------------------------- ##
ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8
STOPSIGNAL SIGINT
EXPOSE 8000/tcp
WORKDIR /workspace/app
# no ENTRYPOINT as we need to be able to run alembic too
CMD [ \
    "uvicorn", \
    "server.app:app", \
    "--host=0.0.0.0", \
    "--port=8000", \
    "--proxy-headers", \
    "--forwarded-allow-ips=*" \
]