# Use Python 3.12 Slim
FROM python:3.12-slim as backend

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Expose port
EXPOSE 8005

# Use a production server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8005"]

# Frontend Stage (for combined deployment)
FROM nginx:alpine as frontend
COPY frontend/ /usr/share/nginx/html/
EXPOSE 80
