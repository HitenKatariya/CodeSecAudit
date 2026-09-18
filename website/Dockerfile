FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Build context = website/  (flat files: app.py, api_client.py, ...)
# Reconstruct the `website` package inside the image so `website.app` imports keep working.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./website/

EXPOSE 10000

# Honor Render's $PORT (defaults to 10000 there too).
CMD ["sh", "-c", "gunicorn website.app:app --bind 0.0.0.0:${PORT:-10000} --workers 2 --timeout 120"]
