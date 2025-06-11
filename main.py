import os, json, requests
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Path, Query
from pydantic import BaseModel

NOTION_VERSION = "2022-06-28"
TOKENS_FILE = "tokens.json"                 # ← onde fica ntn_...
DATABASE_ID_ENV = "NOTION_DATABASE_ID"      # ← opcional: exporte se quiser fixar

def get_token():
    with open(TOKENS_FILE, "r") as f:
        tokens = json.load(f)
    return list(tokens.values())[0]["access_token"]

def notion_headers(token: str, json_ct: bool = True):
    h = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION
    }
    if json_ct:
        h["Content-Type"] = "application/json"
    return h


# ---------- FASTAPI ----------
app = FastAPI()


# ---------- MODELOS ----------
class PostCreate(BaseModel):
    Nome: str
    Status: str = "💡 Ideias para Post"
    Tipo___de___post: str
    Data___de___postagem: str              # YYYY-MM-DD sempre
    Hashtags: Optional[str] = ""
    description: Optional[str] = ""


# ---------- RESOLVE TÍTULO ----------
@app.post("/notion/pages/resolve-title")
def resolve_title_to_page_id(body: dict):
    title = body.get("title", "").strip()
    if not title:
        raise HTTPException(400, "Título não fornecido")

    token = get_token()
    resp = requests.post(
        "https://api.notion.com/v1/search",
        headers=notion_headers(token),
        json={"query": title}
    )
    data = resp.json()
    for res in data.get("results", []):
        nome_raw = res.get("properties", {}).get("Nome", {}).get("title", [])
        nome = nome_raw[0].get("text", {}).get("content", "") if nome_raw else ""
        if nome.lower() == title.lower():
            return {"page_id": res["id"]}
    raise HTTPException(404, "Título não encontrado")


# ---------- CRIAR CARD ----------
@app.post("/notion/create-post")
def create_post(payload: PostCreate):
    token = get_token()
    database_id = os.getenv(DATABASE_ID_ENV) or \
                  payload.dict().get("database_id") or \
                  "2062b868-6ff2-81cf-b7f5-e379236da5cf"

    props = {
        "Nome": {
            "title": [{"text": {"content": payload.Nome}}]
        },
        "Status": {"select": {"name": payload.Status}},
        "Tipo de post": {"select": {"name": payload.Tipo___de___post}},
        "Data de postagem": {"date": {"start": payload.Data___de___postagem}},
        "Hashtags": {"rich_text": [{"text": {"content": payload.Hashtags}}]}
    }

    # cria página
    page = requests.post(
        "https://api.notion.com/v1/pages",
        headers=notion_headers(token),
        json={"parent": {"database_id": database_id}, "properties": props}
    )
    if not page.ok:
        raise HTTPException(page.status_code, page.text)

    page_id = page.json()["id"]

    # adiciona copy se existir
    if payload.description:
        requests.patch(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers=notion_headers(token),
            json={
                "children": [{
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": payload.description}
                        }]
                    }
                }]
            }
        )

    return {"status": "success", "page_id": page_id}


# ---------- ATUALIZAR PROPRIEDADES ----------
@app.patch("/notion/post/{page_id}")
def update_post(page_id: str, body: dict):
    token = get_token()
    props = {
        "Nome": {"title": [{"text": {"content": body.get("Nome", "")}}]},
        "Status": {"select": {"name": body.get("Status")}},
        "Tipo de post": {"select": {"name": body.get('Tipo___de___post') or body.get('Tipo de post')}} ,
        "Hashtags": {"rich_text": [{"text": {"content": body.get("Hashtags", "")}}]},
        "Data de postagem": {"date": {"start": body.get("Data___de___postagem") or body.get("Data de postagem")}}
    }
    resp = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=notion_headers(token),
        json={"properties": props}
    )
    if not resp.ok:
        raise HTTPException(resp.status_code, resp.text)
    return {"status": "success", "details": "Post atualizado"}


# ---------- ATUALIZAR STATUS ----------
@app.patch("/notion/post/{page_id}/status")
def update_status(page_id: str, body: dict):
    token = get_token()
    resp = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=notion_headers(token),
        json={"properties": {"Status": {"select": {"name": body.get("status")}}}}
    )
    if not resp.ok:
        raise HTTPException(resp.status_code, resp.text)
    return {"status": "success"}


# ---------- EXCLUIR (arquivar) ----------
@app.delete("/notion/post/{page_id}")
def delete_post(page_id: str):
    token = get_token()
    resp = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=notion_headers(token),
        json={"archived": True}
    )
    if not resp.ok:
        raise HTTPException(resp.status_code, resp.text)
    return {"status": "success"}


# ---------- ATUALIZAR COPY/LEGENDA ----------
@app.patch("/notion/post/{page_id}/content")
def update_content(page_id: str, body: dict):
    description = body.get("description", "").strip()
    if not description:
        raise HTTPException(400, "Descrição vazia")

    token = get_token()
    # Anexa como novo bloco
    resp = requests.patch(
        f"https://api.notion.com/v1/blocks/{page_id}/children",
        headers=notion_headers(token),
        json={"children": [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": description}
                }]
            }
        }]}
    )
    if not resp.ok:
        raise HTTPException(resp.status_code, resp.text)
    return {"status": "success"}


# ---------- SUMÁRIO (contagens) ----------
@app.get("/notion/summary/{database_id}")
def summary(database_id: str):
    token = get_token()
    resp = requests.post(
        f"https://api.notion.com/v1/databases/{database_id}/query",
        headers=notion_headers(token)
    )
    if not resp.ok:
        raise HTTPException(resp.status_code, resp.text)

    status_count, type_count = {}, {}
    for page in resp.json().get("results", []):
        status = page["properties"]["Status"]["select"]["name"]
        tipo   = page["properties"]["Tipo de post"]["select"]["name"]
        status_count[status] = status_count.get(status, 0) + 1
        type_count[tipo]     = type_count.get(tipo, 0) + 1

    return {"status_summary": status_count, "type_summary": type_count}


# ---------- LISTAR RECENTES ----------
@app.get("/notion/recent/{database_id}")
def recent(database_id: str, limit: int = Query(10, gt=0, le=50)):
    token = get_token()
    resp = requests.post(
        f"https://api.notion.com/v1/databases/{database_id}/query",
        headers=notion_headers(token),
        json={"page_size": limit, "sorts": [{"timestamp": "created_time", "direction": "descending"}]}
    )
    if not resp.ok:
        raise HTTPException(resp.status_code, resp.text)

    pages = []
    for p in resp.json().get("results", []):
        pages.append({
            "id": p["id"],
            "nome": p["properties"]["Nome"]["title"][0]["plain_text"],
            "status": p["properties"]["Status"]["select"]["name"],
            "tipo": p["properties"]["Tipo de post"]["select"]["name"],
            "created": p["created_time"][:10]
        })
    return pages


# ---------- DEBUG: ROTAS ----------
@app.get("/routes")
def list_routes():
    return [route.path for route in app.routes]

# ---------- ANÁLISE DO KANBAN ----------
@app.get("/analyze-kanban")
def analyze_kanban():
    token = get_token()
    database_id = os.getenv(DATABASE_ID_ENV) or "2062b8686ff281cfb7f5e379236da5cf"

    resp = requests.post(
        f"https://api.notion.com/v1/databases/{database_id}/query",
        headers=notion_headers(token)
    )

    if not resp.ok:
        raise HTTPException(resp.status_code, resp.text)

    data = resp.json()
    status_count = {}
    type_count = {}

    for page in data.get("results", []):
        props = page.get("properties", {})
        status = props.get("Status", {}).get("select", {}).get("name", "Indefinido")
        tipo = props.get("Tipo de post", {}).get("select", {}).get("name", "Indefinido")

        status_count[status] = status_count.get(status, 0) + 1
        type_count[tipo] = type_count.get(tipo, 0) + 1

    return {
        "status_summary": status_count,
        "type_summary": type_count
    }
