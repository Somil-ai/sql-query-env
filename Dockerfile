FROM python:3.11-slim

# Create non-root user (HF Spaces requirement)
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install dependencies first (Docker layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Give appuser ownership
RUN chown -R appuser:appuser /app
USER appuser

# HuggingFace Spaces always uses port 7860
EXPOSE 7860

# Start the FastAPI server
CMD ["uvicorn", "app_main:app", "--host", "0.0.0.0", "--port", "7860"]