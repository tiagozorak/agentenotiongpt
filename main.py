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

# ---------- FUNÇÃO AUXILIAR ----------
def safe_get(obj, path, default=None):
    try:
        for key in path:
            obj = obj[key]
        return obj
    except (KeyError, TypeError, IndexError):
        return default

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
        raise HTTPException(400, "Missing title")

    token = get_token()
    resp = requests.post(
        "https://api.notion.com/v1/search",
        headers=notion_headers(token),
        json={"query": title, "sort": {"direction": "descending", "timestamp": "last_edited_time"}}
    )
    data = resp.json()

    for res in data.get("results", []):
        props = res.get("properties", {})
        # Verifica diferentes campos que podem conter o título
        possible_titles = [
            safe_get(props, ["Nome", "title", 0, "text", "content"]),
            safe_get(props, ["📌 Título do Post", "title", 0, "text", "content"])
        ]
        if any(t and t.lower() == title.lower() for t in possible_titles):
            return {"page_id": res["id"]}

    raise HTTPException(404, "Title not found")


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

    # 1. Recupera os blocos filhos (para deletar)
    children = requests.get(
        f"https://api.notion.com/v1/blocks/{page_id}/children",
        headers=notion_headers(token, json_ct=False)
    ).json().get("results", [])

    # 2. Remove os blocos existentes
    for block in children:
        block_id = block["id"]
        requests.patch(
            f"https://api.notion.com/v1/blocks/{block_id}",
            headers=notion_headers(token),
            json={"archived": True}
        )

    # 3. Adiciona novo bloco com a nova legenda
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
    response = requests.post(
        f"https://api.notion.com/v1/databases/{database_id}/query",
        headers=notion_headers(token),
        json={
            "page_size": limit,
            "sorts": [{"timestamp": "created_time", "direction": "descending"}]
        }
    )

    if not response.ok:
        raise HTTPException(response.status_code, response.text)

    posts = []
    for p in response.json()["results"]:
        props = p["properties"]
        post = {
            "id": p["id"],
            "nome": safe_get(props, ["Nome", "title", 0, "plain_text"], "Sem título"),
            "status": safe_get(props, ["Status", "select", "name"], "Não definido"),
            "tipo": safe_get(props, ["Tipo de post", "select", "name"], "Não definido"),
            "data_postagem": safe_get(props, ["Data de postagem", "date", "start"]),
        }
        posts.append(post)

    return posts

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
# ---------- NOVA ROTA COMPATÍVEL ----------
@app.post("/create-idea")
def create_idea(body: dict):
    """
    Compatível com o agente: espera chaves minúsculas (nome, status, tipo, hashtags, data_postagem, descricao).
    Redireciona internamente para a lógica já existente de /notion/create-post.
    """
    payload = PostCreate(
        Nome                = body.get("nome"),
        Status              = body.get("status", "💡 Ideias para Post"),
        Tipo___de___post    = body.get("tipo") or body.get("tipo___de___post"),
        Data___de___postagem= body.get("data_postagem"),
        Hashtags            = body.get("hashtags", ""),
        description         = body.get("descricao", "")
    )
    return create_post(payload)

# ---------- TABELA DE CONTEÚDO PLANEJADO ----------
@app.get("/notion/content-planned/{database_id}")
def list_planned_content(database_id: str):
    token = get_token()
    
    # 1. Lista as páginas da base
    response = requests.post(
        f"https://api.notion.com/v1/databases/{database_id}/query",
        headers=notion_headers(token),
        json={"page_size": 20, "sorts": [{"timestamp": "created_time", "direction": "descending"}]}
    )

    if not response.ok:
        raise HTTPException(response.status_code, response.text)

    pages = []
    for page in response.json().get("results", []):
        page_id = page["id"]

        # 2. Recupera os dados reais da página
        detail = requests.get(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=notion_headers(token)
        )

        if not detail.ok:
            continue

        props = detail.json().get("properties", {})

        pages.append({
            "id": page_id,
            "titulo": safe_get(props, [list(props.keys())[0], "title", 0, "plain_text"], "Sem título"),
            "data_publicacao": safe_get(props, ["📆 Data de Publicação", "date", "start"]),
            "status": safe_get(props, ["📋 Status", "rich_text", 0, "plain_text"]),
            "tipo": safe_get(props, ["🎨 Tipo", "rich_text", 0, "plain_text"]),
            "trafego_pago": safe_get(props, ["🚀 Tráfego Pago?", "select", "name"]),
            "orcamento": safe_get(props, ["💰 Orçamento", "number"]),
            "legenda": safe_get(props, ["✍️ Legenda / Copy", "rich_text", 0, "plain_text"]),
            "plataformas": [item.get("name") for item in safe_get(props, ["📱 Plataforma", "multi_select"], []) or []],
            "feedback": safe_get(props, ["💬 Feedback / Observações", "rich_text", 0, "plain_text"])
        })

    return pages

