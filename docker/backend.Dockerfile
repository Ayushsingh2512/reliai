FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir hatchling
RUN pip install -e .[dev]

# Copy source
COPY backend/ /app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
