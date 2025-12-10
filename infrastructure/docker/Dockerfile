# SDLC Agent Squad Docker Image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY agent_squad_sdlc/ ./agent_squad_sdlc/
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Environment variables (override at runtime)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=local \
    STORAGE_TYPE=memory \
    HOST=0.0.0.0 \
    PORT=8080

# Expose webhook port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command - start webhook server
CMD ["python", "-m", "agent_squad_sdlc.handlers.cli_handler", "serve"]
