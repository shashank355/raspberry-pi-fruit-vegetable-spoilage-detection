FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (OpenCV runtime & curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code and assets
COPY . .

# Download models if not present in build context
RUN mkdir -p artifacts/models && \
    if [ ! -f artifacts/models/mobilenetv2_baseline.keras ]; then \
      curl -L -o artifacts/models/mobilenetv2_baseline.keras https://huggingface.co/samithcs/Classifier_Fruits_Vegetables/resolve/main/mobilenetv2_baseline.keras; \
    fi && \
    if [ ! -f artifacts/models/category_classifier.keras ]; then \
      curl -L -o artifacts/models/category_classifier.keras https://huggingface.co/samithcs/Category_Classifier/resolve/main/category_classifier.keras; \
    fi

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/api/metadata || exit 1

CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
