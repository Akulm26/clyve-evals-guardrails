# ghcr.io/akulm26/gtm-evals
#   docker run --rm -v "$PWD:/work" ghcr.io/akulm26/gtm-evals gate workflows/*.yaml
FROM python:3.12-slim
LABEL org.opencontainers.image.source="https://github.com/Akulm26/clyve-evals-guardrails" \
      org.opencontainers.image.description="gtm-evals: evals and guardrails for AI GTM engineering" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.authors="Akul S. Malhotra (@Akulm26)"
WORKDIR /opt/gtm-evals
COPY pyproject.toml README.md LICENSE NOTICE CHANGELOG.md ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd -m gtm
USER gtm
WORKDIR /work
ENTRYPOINT ["gtm-evals"]
CMD ["--help"]
