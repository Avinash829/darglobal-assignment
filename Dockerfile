# ---------- Stage 1: build the React frontend ----------
FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: Python API that also serves the built frontend ----------
FROM python:3.12-slim

# Run as a normal user, not root.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1
WORKDIR /home/user/app

COPY --chown=user backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir --user -r backend/requirements.txt

# Download the embedding model at build time, so the first question is fast.
RUN python -c "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction as E; E()(['warm up'])"

COPY --chown=user backend/ backend/
COPY --chown=user data/ data/
COPY --from=frontend --chown=user /frontend/dist frontend/dist

WORKDIR /home/user/app/backend
# Hosting platforms (e.g. Render) pass the port in $PORT; 7860 is the local default.
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
