from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv
import os
import requests

load_dotenv()  # Carrega variáveis do .env

app = FastAPI()

NOTION_CLIENT_ID = os.getenv("20ed872b-594c-80e5-9195-0037c1c67667")
NOTION_CLIENT_SECRET = os.getenv("secret_K7LeWaG2hVzTF8sueYgCGrMsF9Ufi6YHrIe4wRJSa8K")
NOTION_REDIRECT_URI = os.getenv("https://agentenotiongpt.onrender.com/auth/callback")

NOTION_AUTHORIZE_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"

@app.get("/auth/notion")
def start_oauth():
    auth_url = (
        f"{NOTION_AUTHORIZE_URL}?client_id={NOTION_CLIENT_ID}"
        f"&response_type=code&owner=user&redirect_uri={NOTION_REDIRECT_URI}"
    )
    return RedirectResponse(auth_url)

@app.get("/auth/callback")
def oauth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return JSONResponse(status_code=400, content={"error": "Código não encontrado na URL"})

    token_response = requests.post(
        NOTION_TOKEN_URL,
        auth=(NOTION_CLIENT_ID, NOTION_CLIENT_SECRET),
        headers={"Content-Type": "application/json"},
        json={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": NOTION_REDIRECT_URI
        }
    )

    if token_response.status_code != 200:
        return JSONResponse(status_code=token_response.status_code, content=token_response.json())

    return token_response.json()  # Aqui você pode salvar o token num banco ou arquivo
