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

# Schema de mapeamento de campos

database_schema = {
    "Nome": lambda v: {"title": [{"text": {"content": v}}]},
    "Status": lambda v: {"select": {"name": v}},
    "Tipo de post": lambda v: {"select": {"name": v}},
    "Hashtags": lambda v: {"rich_text": [{"text": {"content": v}}]},
    "Data de postagem": lambda v: {"date": {"start": v}}
}

# PATCH - Atualizar post existente
@app.patch("/notion/post/{page_id}")
def update_post(page_id: str, payload: dict):
    try:
        with open("tokens.json") as f:
            tokens = json.load(f)
        token = list(tokens.values())[0]["access_token"]
    except:
        return JSONResponse(status_code=500, content={"error": "Token inválido"})

    properties = {}
    for campo, valor in payload.items():
        if campo in database_schema:
            properties[campo] = database_schema[campo](valor)

    r = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        },
        json={"properties": properties}
    )
    return {"message": "Post atualizado", "notion_response": r.json()}

# POST - Atualizar status
@app.post("/notion/update_status")
def update_status(data: dict):
    page_id = data.get("page_id")
    novo_status = data.get("status")
    return update_post(page_id, {"Status": novo_status})

# DELETE - Arquivar post
@app.delete("/notion/post/{page_id}")
def delete_post(page_id: str):
    try:
        with open("tokens.json") as f:
            tokens = json.load(f)
        token = list(tokens.values())[0]["access_token"]
    except:
        return JSONResponse(status_code=500, content={"error": "Token inválido"})

    r = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        },
        json={"archived": True}
    )
    return {"message": "Post arquivado", "notion_response": r.json()}

# GET - Resumo por status e tipo de post
@app.get("/notion/summary/{database_id}")
def get_summary(database_id: str):
    try:
        with open("tokens.json") as f:
            tokens = json.load(f)
        token = list(tokens.values())[0]["access_token"]
    except:
        return JSONResponse(status_code=500, content={"error": "Token inválido"})

    r = requests.post(
        f"https://api.notion.com/v1/databases/{database_id}/query",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
    )
    if r.status_code != 200:
        return JSONResponse(status_code=r.status_code, content=r.json())

    data = r.json()
    status_count = {}
    tipo_count = {}

    for item in data.get("results", []):
        props = item.get("properties", {})
        status = props.get("Status", {}).get("select", {}).get("name")
        tipo = props.get("Tipo de post", {}).get("select", {}).get("name")

        if status:
            status_count[status] = status_count.get(status, 0) + 1
        if tipo:
            tipo_count[tipo] = tipo_count.get(tipo, 0) + 1

    return {"totais_por_tipo": tipo_count, "totais_por_status": status_count}

# GET - Ler um post específico
@app.get("/notion/post/{page_id}")
def get_post(page_id: str):
    try:
        with open("tokens.json") as f:
            tokens = json.load(f)
        token = list(tokens.values())[0]["access_token"]
    except:
        return JSONResponse(status_code=500, content={"error": "Token inválido"})

    r = requests.get(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28"
        }
    )
    return r.json()
