# egSYS JiraView — Docker (hardening espelho Orion: 512m/1.0cpu/150pids, não-privilegiado)
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY deploy /app/deploy
COPY frontend /app/frontend

EXPOSE 8090

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8090"]
