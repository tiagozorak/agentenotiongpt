# Dockerfile
FROM python:3.11-slim

# Diretório da aplicação
WORKDIR /app

# Copia os arquivos
COPY . .

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Expõe a porta padrão do FastAPI
EXPOSE 8000

# Comando para iniciar o servidor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
