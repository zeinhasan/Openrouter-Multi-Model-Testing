# Gunakan image Python resmi
FROM python:3.10-slim

# Set workdir
WORKDIR /app

# Copy requirements dan install dependency
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy semua file aplikasi ke dalam image
COPY . .

# Expose port Streamlit
EXPOSE 8501

# Jalankan Streamlit
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
