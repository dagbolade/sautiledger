FROM python:3.11-slim

WORKDIR /app

# editable install keeps the repo layout (packs/ and static/ resolve
# relative to the source tree, not site-packages)
COPY pyproject.toml README.md ./
COPY src ./src
COPY packs ./packs
COPY static ./static
RUN pip install --no-cache-dir -e .

# the ledger lives on a mounted volume so redeploys never lose a trader's book
ENV SAUTI_DB=/data/ledger.db

CMD ["sh", "-c", "uvicorn sautiledger.api:app --host 0.0.0.0 --port ${PORT:-8090}"]
