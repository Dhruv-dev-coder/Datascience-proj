FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose Streamlit default port
EXPOSE 8501

# Run benchmark seeder then launch Streamlit dashboard
CMD ["sh", "-c", "python scripts/seed_sample_data.py && streamlit run dashboard/app.py --server.port=8501 --server.address=0.0.0.0"]
