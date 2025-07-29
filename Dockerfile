# Gunakan image Python resmi
FROM python:3.10-slim

# Tetapkan direktori kerja di dalam container
WORKDIR /app

# Salin requirements.txt dan app.py ke dalam container
COPY requirements.txt .
COPY monevunsud.py .

# Install dependensi Python
RUN pip install --no-cache-dir -r requirements.txt

# Jalankan aplikasi
CMD ["python", "monevunsud.py"]
