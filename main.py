# main.py

from fastapi import FastAPI, Request, Path
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv
import os
import requests
import json
from datetime import datetime

load_dotenv()
app = FastAPI()

NOTION_CLIENT_ID = os.getenv("NOTION_CLIENT_ID")
NOTION_CLIENT_SECRET = os.getenv("NOTION_CLIENT_SECRET")
NOTION_REDIRECT_URI = os.getenv("NOTION_REDIRECT_URI")

NOTION_AUTHORIZE_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"

BANCO_DE_IDEIAS_ID = "2062b868-6ff2-81cf-b7f5-e379236da5cf"

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

    data = token_response.json()
    workspace_id = data.get("workspace_id")

    data_to_save = {
        workspace_id: {
            "user": data["owner"]["user"]["name"],
            "email": data["owner"]["user"]["person"]["email"],
            "access_token": data["access_token"],
            "workspace_name": data["workspace_name"],
            "bot_id": data["bot_id"],
            "created_at": datetime.utcnow().isoformat()
        }
    }

    with open("tokens.json", "w") as f:
        json.dump(data_to_save, f, indent=2)

    return JSONResponse(content={"message": "Token salvo com sucesso", "workspace_id": workspace_id})

@app.get("/notion/databases/simplified")
def simplified_databases(workspace_id: str):
    try:
        with open("tokens.json", "r") as file:
            tokens = json.load(file)

        if workspace_id not in tokens:
            return JSONResponse(status_code=404, content={"error": "Workspace ID não encontrado"})

        access_token = tokens[workspace_id]["access_token"]
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Erro ao carregar token: {str(e)}"})

    response = requests.post(
        "https://api.notion.com/v1/search",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        },
        json={"filter": {"property": "object", "value": "database"}}
    )

    if response.status_code != 200:
        return JSONResponse(status_code=response.status_code, content=response.json())

    data = response.json()
    simplified = [
        {
            "id": db["id"],
            "title": (
                db.get("title", [{}])[0].get("text", {}).get("content", "")
                if db.get("title") else "(sem título)"
            ),
            "url": db.get("url"),
            "created_time": db.get("created_time")
        }
        for db in data.get("results", [])
    ]

    return {"databases": simplified}

@app.post("/notion/pages/resolve-title")
def resolve_page_id_by_title(payload: dict):
    title = payload.get("title")
    if not title:
        return JSONResponse(status_code=400, content={"error": "Título não informado"})

    try:
        with open("tokens.json", "r") as file:
            tokens = json.load(file)
        token = list(tokens.values())[0]["access_token"]
    except:
        return JSONResponse(status_code=500, content={"error": "Token inválido"})

    response = requests.post(
        f"https://api.notion.com/v1/databases/{BANCO_DE_IDEIAS_ID}/query",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
    )

    if response.status_code != 200:
        return JSONResponse(status_code=response.status_code, content=response.json())

    data = response.json()
    for result in data.get("results", []):
        nome = result.get("properties", {}).get("Nome", {}).get("title", [{}])[0].get("text", {}).get("content", "")
        if nome.lower().strip() == title.lower().strip():
            return {"page_id": result.get("id")}

    return JSONResponse(status_code=404, content={"error": "Título não encontrado"})
