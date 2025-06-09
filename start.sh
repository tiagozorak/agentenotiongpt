#!/bin/bash
# start.sh: Ativa o ambiente virtual e executa o servidor FastAPI com Uvicorn

source venv/bin/activate
exec python -m uvicorn main:app --host 0.0.0.0 --port $PORT
