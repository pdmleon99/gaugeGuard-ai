FROM python:3.12.5-slim

WORKDIR /app

# Install deps first (better layer caching)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Copy sample data (pre-seeded CSVs — regenerated at startup if missing)
COPY data/ /app/data/

# Path overrides for Docker environment
ENV GAUGEDATA_DIR=/app/data
ENV DATABASE_URL=sqlite:///./gaugeGuard.db

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
