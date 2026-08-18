# =============================================================================
# Stage 1: Builder - Install build dependencies and compile Python packages
# =============================================================================
FROM python:3.11-slim-bookworm AS builder

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies needed to compile Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment for clean dependency isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy dependency files and install Python packages
WORKDIR /build
COPY pyproject.toml ./
# If requirements.txt exists, copy it too (fallback)
COPY requirements*.txt* ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -e . 2>/dev/null \
    || pip install --no-cache-dir -r requirements.txt 2>/dev/null \
    || echo "No dependency file found; dependencies will need to be added"

# =============================================================================
# Stage 2: Runtime - Lean production image
# =============================================================================
FROM python:3.11-slim-bookworm AS runtime

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install runtime system dependencies:
# - Tesseract OCR with Thai and English language data
# - WeasyPrint runtime dependencies (cairo, pango, gdk-pixbuf)
# - Thai fonts (TH Sarabun New / fonts-thai-tlwg)
# - curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Tesseract OCR
    tesseract-ocr \
    tesseract-ocr-tha \
    tesseract-ocr-eng \
    # WeasyPrint runtime deps
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libxml2 \
    libffi8 \
    shared-mime-info \
    # Thai fonts
    fonts-thai-tlwg \
    # PostgreSQL client library (for asyncpg/psycopg2)
    libpq5 \
    # Health check utility
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled Python packages from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Set up application directory
WORKDIR /app
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini pyproject.toml ./
COPY scripts ./scripts

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the backend API port
EXPOSE 4000

# Health check: verify the /health endpoint responds
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
    CMD curl -f http://localhost:4000/health || exit 1

# Start the FastAPI application with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4000"]
