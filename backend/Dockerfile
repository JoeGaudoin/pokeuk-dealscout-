FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching (from backend folder in build context)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ ./backend/

# Set Python path so 'backend' package can be found
ENV PYTHONPATH=/app

# Create non-root user
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run migrations then start server
CMD cd /app/backend && alembic upgrade head && cd /app && uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
