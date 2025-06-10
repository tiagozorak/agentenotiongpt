from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv
import os
import requests

load_dotenv()
app = FastAPI()

NOTION_CLIENT_ID = os.getenv("NOTION_CLIENT_ID")
NOTION_CLIENT_SECRET = os.getenv("NOTION_CLIENT_SECRET")
NOTION_REDIRECT_URI = os.getenv("NOTION_REDIRECT_URI")

NOTION_AUTHORIZE_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"

# ⚠️ Substitua por seu token temporariamente (ou implemente armazenamento em breve)
TEMP_ACCESS_TOKEN = "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"

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

    return token_response.json()

@app.get("/notion/databases")
def list_databases():
    response = requests.post(
        "https://api.notion.com/v1/search",
        headers={
            "Authorization": f"Bearer {TEMP_ACCESS_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        },
        json={
            "filter": {
                "property": "object",
                "value": "database"
            }
        }
    )

    if response.status_code != 200:
        return JSONResponse(status_code=response.status_code, content=response.json())

    return response.json()
@app.get("/notion/databases/simplified")
def simplified_databases():
    access_token = os.getenv("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")  # temporário, podemos mudar
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
