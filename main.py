import os, json, requests
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Path, Query
from pydantic import BaseModel

NOTION_VERSION = "2022-06-28"
TOKENS_FILE = "tokens.json"
DATABASE_ID_ENV = "NOTION_DATABASE_ID"
CONTENT_PLANNED_DATABASE_ID = "2062b8686ff281d890a9fd41641b56fb"
KANBAN_DATABASE_ID = "2062b868-6ff2-81cf-b7f5-e379236da5cf"

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
@app.get("/notion/content-planned/{_}")
def list_planned_content(_: str):
    token = get_token()
    database_id = CONTENT_PLANNED_DATABASE_ID
    resp = requests.post(
        f"https://api.notion.com/v1/databases/{database_id}/query",
        headers=notion_headers(token),
        json={"page_size": 20, "sorts": [{"timestamp": "created_time", "direction": "descending"}]}
    )
    if not resp.ok:
        raise HTTPException(resp.status_code, resp.text)

    pages = []
    for p in resp.json().get("results", []):
        props = p["properties"]
        pages.append({
            "id": p["id"],
            "titulo": safe_get(props, ["📌 Título do Post", "title", 0, "plain_text"], "Sem título"),
            "data_publicacao": safe_get(props, ["📆 Data de Publicação", "date", "start"]),
            "status": safe_get(props, ["📋 Status", "rich_text", 0, "plain_text"]),
            "tipo": safe_get(props, ["🎨 Tipo", "rich_text", 0, "plain_text"]),
            "trafego_pago": safe_get(props, ["🚀 Tráfego Pago?", "select", "name"]),
            "orcamento": safe_get(props, ["💰 Orçamento", "number"]),
            "legenda": safe_get(props, ["✍️ Legenda / Copy", "rich_text", 0, "plain_text"]),
            "plataformas": [tag["name"] for tag in safe_get(props, ["📱 Plataforma", "multi_select"], [])],
            "feedback": safe_get(props, ["💬 Feedback / Observações", "rich_text", 0, "plain_text"]),
            "engajamento": {
                "curtidas_1h": safe_get(props, ["❤️ Curtidas (1h)", "number"]),
                "curtidas_24h": safe_get(props, ["❤️ Curtidas (24h)", "number"]),
                "curtidas_7d": safe_get(props, ["❤️ Curtidas (7d)", "number"]),
                "comentarios_1h": safe_get(props, ["💬 Comentários (1h)", "number"]),
                "comentarios_24h": safe_get(props, ["💬 Comentários (24h)", "number"]),
                "comentarios_7d": safe_get(props, ["💬 Comentários (7d)", "number"]),
                "compartilhamentos_1h": safe_get(props, ["🔁 Compartilhamentos (1h)", "number"]),
                "compartilhamentos_24h": safe_get(props, ["🔁 Compartilhamentos (24h)", "number"]),
                "compartilhamentos_7d": safe_get(props, ["🔁 Compartilhamentos (7d)", "number"]),
                "salvamentos_1h": safe_get(props, ["💾 Salvamentos (1h)", "number"]),
                "salvamentos_24h": safe_get(props, ["💾 Salvamentos (24h)", "number"]),
                "salvamentos_7d": safe_get(props, ["💾 Salvamentos (7d)", "number"]),
                "alcance_1h": safe_get(props, ["👀 Alcance (1h)", "number"]),
                "alcance_24h": safe_get(props, ["👀 Alcance (24h)", "number"]),
                "alcance_7d": safe_get(props, ["👀 Alcance (7d)", "number"]),
                "engajamento_total": safe_get(props, ["📈 Engajamento total", "number"]),
                "taxa_engajamento": safe_get(props, ["📊 Taxa de Engajamento", "number"]),
            }
        })

    return pages

# ---------- POSTS COM TRÁFEGO PAGO ----------
@app.get("/notion/content-paid/{database_id}")
def list_paid_content(database_id: str):
    token = get_token()
    resp = requests.post(
        f"https://api.notion.com/v1/databases/{database_id}/query",
        headers=notion_headers(token),
        json={
            "page_size": 50,
            "filter": {
                "property": "🚀 Tráfego Pago?",
                "select": {"equals": "Sim"}
            },
            "sorts": [{"timestamp": "created_time", "direction": "descending"}]
        }
    )
    if not resp.ok:
        raise HTTPException(resp.status_code, resp.text)

    pages = []
    for p in resp.json().get("results", []):
        props = p["properties"]
        pages.append({
            "id": p["id"],
            "titulo": safe_get(props, ["📌 Título do Post", "title", 0, "plain_text"], "Sem título"),
            "data_publicacao": safe_get(props, ["📆 Data de Publicação", "date", "start"]),
            "status": safe_get(props, ["📋 Status", "rich_text", 0, "plain_text"]),
            "tipo": safe_get(props, ["🎨 Tipo", "rich_text", 0, "plain_text"]),
            "trafego_pago": safe_get(props, ["🚀 Tráfego Pago?", "select", "name"]),
            "orcamento": safe_get(props, ["💰 Orçamento", "number"]),
            "legenda": safe_get(props, ["✍️ Legenda / Copy", "rich_text", 0, "plain_text"]),
            "plataformas": [tag["name"] for tag in safe_get(props, ["📱 Plataforma", "multi_select"], [])],
            "feedback": safe_get(props, ["💬 Feedback / Observações", "rich_text", 0, "plain_text"]),
            "engajamento": {
                "curtidas_1h": safe_get(props, ["❤️ Curtidas (1h)", "number"]),
                "curtidas_24h": safe_get(props, ["❤️ Curtidas (24h)", "number"]),
                "curtidas_7d": safe_get(props, ["❤️ Curtidas (7d)", "number"]),
                "comentarios_1h": safe_get(props, ["💬 Comentários (1h)", "number"]),
                "comentarios_24h": safe_get(props, ["💬 Comentários (24h)", "number"]),
                "comentarios_7d": safe_get(props, ["💬 Comentários (7d)", "number"]),
                "compartilhamentos_1h": safe_get(props, ["🔁 Compartilhamentos (1h)", "number"]),
                "compartilhamentos_24h": safe_get(props, ["🔁 Compartilhamentos (24h)", "number"]),
                "compartilhamentos_7d": safe_get(props, ["🔁 Compartilhamentos (7d)", "number"]),
                "salvamentos_1h": safe_get(props, ["💾 Salvamentos (1h)", "number"]),
                "salvamentos_24h": safe_get(props, ["💾 Salvamentos (24h)", "number"]),
                "salvamentos_7d": safe_get(props, ["💾 Salvamentos (7d)", "number"]),
                "alcance_1h": safe_get(props, ["👀 Alcance (1h)", "number"]),
                "alcance_24h": safe_get(props, ["👀 Alcance (24h)", "number"]),
                "alcance_7d": safe_get(props, ["👀 Alcance (7d)", "number"]),
                "engajamento_total": safe_get(props, ["📈 Engajamento total", "number"]),
                "taxa_engajamento": safe_get(props, ["📊 Taxa de Engajamento", "number"]),
            }
        })

    return pages


@app.get("/notion/insight/{page_id}")
async def gerar_insight_individual(page_id: str):
    try:
        data = await buscar_dados_postagem(page_id)

        if not data:
            return {"erro": "Postagem não encontrada ou dados ausentes."}

        engajamento = data.get("engajamento", {})
        taxa = engajamento.get("taxa_engajamento")
        taxa_formatada = f"{taxa:.2f}" if taxa is not None else "0"

        # Gera o prompt com base nos dados obtidos
        prompt = f"""
Você é um especialista em marketing de conteúdo. Analise os dados abaixo de uma publicação em redes sociais com base em suas métricas de engajamento e orçamento, e gere um insight objetivo e estratégico sobre seu desempenho, apontando possíveis melhorias para conteúdos futuros. Seja direto, claro e últil. Os dados são:

Título: {data.get("titulo", "Sem título")}
Tipo: {data.get("tipo", "Não informado")}
Data de Publicação: {data.get("data_publicacao", "Não informado")}
Tráfego Pago: {data.get("trafego_pago", "Não informado")}
Orçamento: {data.get("orcamento", "0")}
Plataformas: {", ".join(data.get("plataformas", []))}

Métricas de Engajamento (em até 7 dias):
Curtidas: {data.get("curtidas_7d", 0)}
Comentários: {data.get("comentarios_7d", 0)}
Compartilhamentos: {data.get("compartilhamentos_7d", 0)}
Salvamentos: {data.get("salvamentos_7d", 0)}
Alcance: {data.get("alcance_7d", 0)}
Taxa de Engajamento: {taxa_formatada}%
        """

        insight = await gerar_resposta(prompt)
        return {"insight": insight}

    except Exception as e:
        return {"erro": str(e)}


# ---------- FUNÇÕES PARA INSIGHTS INDIVIDUAIS ----------
async def buscar_dados_postagem(page_id):
    token = get_token()
    url = f"https://api.notion.com/v1/pages/{page_id}"
    resp = requests.get(url, headers=notion_headers(token))

    if not resp.ok:
        raise HTTPException(resp.status_code, resp.text)

    props = resp.json().get("properties", {})

    plataformas_raw = safe_get(props, ["📱 Plataforma", "multi_select"], [])
    plataformas = [tag["name"] for tag in plataformas_raw if "name" in tag]

    taxa_engajamento = safe_get(props, ["📊 Taxa de Engajamento", "formula", "number"],
                                safe_get(props, ["📊 Taxa de Engajamento", "number"], 0))

    return {
        "titulo": safe_get(props, ["📌 Título do Post", "title", 0, "plain_text"], "Sem título"),
        "tipo": safe_get(props, ["🎨 Tipo", "rich_text", 0, "plain_text"]),
        "data_publicacao": safe_get(props, ["📆 Data de Publicação", "date", "start"]),
        "trafego_pago": safe_get(props, ["🚀 Tráfego Pago?", "select", "name"]),
        "orcamento": safe_get(props, ["💰 Orçamento", "number"]),
        "plataformas": plataformas,
        "curtidas_7d": safe_get(props, ["❤️ Curtidas (7d)", "number"]),
        "comentarios_7d": safe_get(props, ["💬 Comentários (7d)", "number"]),
        "compartilhamentos_7d": safe_get(props, ["🔁 Compartilhamentos (7d)", "number"]),
        "salvamentos_7d": safe_get(props, ["💾 Salvamentos (7d)", "number"]),
        "alcance_7d": safe_get(props, ["👀 Alcance (7d)", "number"]),
        "taxa_engajamento": taxa_engajamento
    }

async def gerar_resposta(prompt: str):
    from openai import AsyncOpenAI
    client = AsyncOpenAI()

    chat = await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return chat.choices[0].message.content.strip()


# ---------- ANÁLISE HISTÓRICA ----------
@app.get("/notion/insight/history")
async def gerar_insight_historico():
    token = get_token()
    database_id = CONTENT_PLANNED_DATABASE_ID

    response = requests.post(
        f"https://api.notion.com/v1/databases/{database_id}/query",
        headers=notion_headers(token),
        json={"page_size": 50, "sorts": [{"timestamp": "created_time", "direction": "descending"}]}
    )

    if not response.ok:
        raise HTTPException(response.status_code, response.text)

    posts = []
    for p in response.json().get("results", []):
        props = p["properties"]
        posts.append({
            "titulo": safe_get(props, ["📌 Título do Post", "title", 0, "plain_text"], "Sem título"),
            "tipo": safe_get(props, ["🎨 Tipo", "rich_text", 0, "plain_text"]),
            "trafego_pago": safe_get(props, ["🚀 Tráfego Pago?", "select", "name"]),
            "orcamento": safe_get(props, ["💰 Orçamento", "number"], 0),
            "taxa_engajamento": safe_get(props, ["📊 Taxa de Engajamento", "formula", "number"],
                                           safe_get(props, ["📊 Taxa de Engajamento", "number"], 0)),
            "engajamento_total": safe_get(props, ["📈 Engajamento total", "formula", "number"],
                                           safe_get(props, ["📈 Engajamento total", "number"], 0)),
        })

    exemplos = [
        f"Título: {p['titulo']} | Tipo: {p['tipo']} | Tráfego: {p['trafego_pago']} | Orçamento: R${p['orcamento']} | Engajamento: {p['engajamento_total']} | Taxa: {p['taxa_engajamento']:.2f}%"
        for p in posts[:10] if p["titulo"] != "Sem título"
    ]

    prompt = f"""
Você é um estrategista de conteúdo. Analise os dados de desempenho de posts anteriores listados abaixo e gere insights sobre o que funcionou bem e o que pode ser melhorado. Identifique padrões que ajudem a orientar a criação de novos conteúdos com base em tipo, tráfego pago e taxa de engajamento.

Posts:
{chr(10).join(exemplos)}

Seja claro, direto e forneça recomendações práticas.
"""

    insight = await gerar_resposta(prompt)
    return {"insight": insight}
