FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data logs exports/profit

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000 8501

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
