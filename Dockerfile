FROM python:3.11-slim

WORKDIR /app

# Install minimal build tools for native Python wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy application files
COPY . .

# Hugging Face Spaces standard port is 7860
ENV PORT=7860
EXPOSE 7860

# Launch FastAPI ASGI server
CMD ["uvicorn", "smart:app", "--host", "0.0.0.0", "--port", "7860"]
