FROM python:3.11-slim

# Install system dependencies for pandas, psycopg2, etc.
RUN apt-get update && apt-get install -y \
  build-essential \
  gcc \
  g++ \
  libpq-dev \
  python3-dev \
  curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY ./app /app
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
