FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=config.settings.development
RUN python manage.py collectstatic --noinput

ENV DJANGO_SETTINGS_MODULE=config.settings.production
RUN sed -i 's/\r$//' /app/scripts/docker-entrypoint.sh && chmod +x /app/scripts/docker-entrypoint.sh
EXPOSE 8000
CMD ["./scripts/docker-entrypoint.sh"]
