from fastapi import FastAPI, Request
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
from fastapi import Body

@app.post("/notion/databases/{database_id}/add_post")
def create_post(database_id: str, workspace_id: str, body: dict = Body(...)):
    try:
        with open("tokens.json", "r") as file:
            tokens = json.load(file)
        if workspace_id not in tokens:
            return JSONResponse(status_code=404, content={"error": "Workspace ID não encontrado"})
        access_token = tokens[workspace_id]["access_token"]
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Erro ao carregar token: {str(e)}"})

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    # Monta o payload com os campos usados na sua database
    new_page = {
        "parent": {"database_id": database_id},
        "properties": {
            "Nome": {
                "title": [{
                    "text": {"content": body.get("Nome", "Sem título")}
                }]
            },
            "Status": {
                "select": {"name": body.get("Status")}
            },
            "Tipo de post": {
                "select": {"name": body.get("Tipo de post")}
            },
            "Data de postagem": {
                "date": {"start": body.get("Data de postagem")}
            },
            "Hashtags": {
                "rich_text": [{
                    "text": {"content": body.get("Hashtags", "")}
                }]
            }
        }
    }

    response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=new_page)

    if response.status_code != 200:
        return JSONResponse(status_code=response.status_code, content=response.json())

    return JSONResponse(status_code=201, content={"message": "Post criado com sucesso", "notion_response": response.json()})
