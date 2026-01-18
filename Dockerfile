FROM python:3.11-slim

WORKDIR /app

# Instalace systémových závislostí
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Kopírování requirements a instalace Python závislostí
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopírování aplikace
COPY app/ /app/app/
COPY templates/ /app/templates/
COPY static/ /app/static/

# Vytvoření adresáře pro binární soubory (bude mapován jako volume)
RUN mkdir -p /app/binaries

# Exponování portu
EXPOSE 8000

# Spuštění aplikace
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
