FROM python:3.11-slim

# Security: run as non-root
RUN useradd -m -u 1000 financeos

WORKDIR /app

# Install system deps for pdfplumber
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY --chown=financeos:financeos . .

USER financeos

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "120", "run:app"]
