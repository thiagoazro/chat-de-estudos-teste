FROM python:3.11-slim

WORKDIR /app

# Copia e instala dependências primeiro (cache de layer do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY . .

# Porta que o Render vai expor
EXPOSE 8000

# Uvicorn em modo produção (sem reload)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
