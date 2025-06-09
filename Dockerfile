# Usa uma imagem leve do Python 3.11
FROM python:3.11-slim

# Define diretório de trabalho dentro do container
WORKDIR /app

# Copia arquivos de dependência primeiro para cache otimizado
COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante dos arquivos da aplicação
COPY . .

# Expõe a porta que o Render irá mapear (8000 é padrão para Uvicorn)
EXPOSE 8000

# Comando padrão para iniciar o servidor FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
