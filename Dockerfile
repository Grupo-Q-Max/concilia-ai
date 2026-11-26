# ==========================================
# ETAPA 1: Compilação do Frontend (Next.js)
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ==========================================
# ETAPA 2: Runtime do Backend (Python + FastAPI)
# ==========================================
FROM python:3.11-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    WEBSITES_PORT=8000

# Dependências mínimas de compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copia o backend e a pasta estática compilada do frontend
COPY backend/ ./backend/
COPY --from=frontend-builder /app/frontend/out ./frontend/out

WORKDIR /app/backend

# Garante pasta de dados/banco de dados
RUN mkdir -p data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
