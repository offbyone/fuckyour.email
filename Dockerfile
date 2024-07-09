# build stage
FROM python:3.12-alpine AS builder

# install PDM
RUN pip install -U pip setuptools wheel
RUN pip install pdm

# copy files
COPY pyproject.toml pdm.lock /project/

# install dependencies and project
WORKDIR /project
RUN pdm install --prod --no-lock --no-editable

# run stage
FROM python:3.12-alpine

RUN apk update && apk add ca-certificates iptables ip6tables bash && rm -rf /var/cache/apk/*

# retrieve packages from build stage
ENV PYTHONPATH=/project/__pypackages__
COPY . /project/
COPY --from=builder /project/.venv /project/.venv

# Service scripts
COPY docker/start.sh /app/start.sh
WORKDIR /project

EXPOSE 8000

# set command/entrypoint, adapt to fit your needs
CMD ["/app/start.sh"]
