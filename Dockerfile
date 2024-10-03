FROM python:3.12-slim


WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt


COPY . .


ENV DEFAULT_IMAGE_PATH='/default/path'
ENV CACHE_TYPE='SimpleCache'
ENV CACHE_TIMEOUT=60



CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
