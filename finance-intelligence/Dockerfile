FROM node:24-bookworm-slim AS frontend-build

WORKDIR /app

COPY package.json package-lock.json ./
COPY frontend/package.json ./frontend/package.json
RUN npm ci --include=dev

COPY frontend ./frontend
RUN npm run build


FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY src ./src
COPY data ./data
COPY prompts ./prompts
COPY DATA_DICTIONARY.md ./
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

RUN useradd --create-home appuser
USER appuser

EXPOSE 10000

CMD ["sh", "-c", "exec python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]