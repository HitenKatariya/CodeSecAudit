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

CMD ["gunicorn", "website.app:app", "--bind", "0.0.0.0:10000"]
