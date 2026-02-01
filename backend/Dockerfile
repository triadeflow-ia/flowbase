# Dockerfile do backend FlowBase - FastAPI para produção
# Build: docker build -t flowbase-backend ./backend
# Run:   docker run -p 8000:8000 --env-file .env flowbase-backend

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
