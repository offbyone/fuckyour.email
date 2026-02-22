ARG PYTHON_VERSION=3.14-slim

FROM python:${PYTHON_VERSION}

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app

RUN mkdir -p /code

WORKDIR /code

# Security-conscious organizations should package/review uv themselves.
COPY --from=ghcr.io/astral-sh/uv:0.4.18 /uv /bin/uv

COPY pyproject.toml uv.lock /code/
RUN --mount=type=cache,target=/root/.cache <<EOT
cd /_lock
uv sync \
    --frozen \
    --no-dev \
    --no-sources \
    --no-install-project
EOT

COPY . /code
RUN --mount=type=cache,target=/root/.cache \
    uv pip install \
        --python=$UV_PROJECT_ENVIRONMENT \
        --no-deps \
        /code

EXPOSE 8000

CMD ["/app/bin/gunicorn","--bind",":8000","--workers","2","fuckyouremail.wsgi"]
