
import json
import requests
from fastapi import FastAPI

app = FastAPI()


@app.post("/notion/pages/resolve-title")
def resolve_title_to_page_id(body: dict):
    title = body.get("title", "").strip()
    if not title:
        return {"error": "Título não fornecido"}

    try:
        with open("tokens.json", "r") as file:
            tokens = json.load(file)
        token = list(tokens.values())[0]["access_token"]

        search = requests.post(
            "https://api.notion.com/v1/search",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            },
            json={"query": title}
        )

        data = search.json()
        for result in data.get("results", []):
            nome_raw = result.get("properties", {}).get("Nome", {}).get("title", [])
            nome = nome_raw[0].get("text", {}).get("content", "") if nome_raw else ""
            if nome.strip().lower() == title.lower():
                return {"page_id": result.get("id")}

        return {"error": "Título não encontrado"}, 404

    except Exception as e:
        return {"error": str(e)}, 500


@app.patch("/notion/post/{page_id}")
def update_post(page_id: str, body: dict):
    try:
        with open("tokens.json", "r") as file:
            tokens = json.load(file)
        token = list(tokens.values())[0]["access_token"]

        response = requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            },
            json={
                "properties": {
                    "Nome": {"title": [{"text": {"content": body.get("Nome", "")}}]},
                    "Status": {"select": {"name": body.get("Status")}},
                    "Tipo de post": {"select": {"name": body.get("Tipo___de___post") or body.get("Tipo de post")}},
                    "Hashtags": {"rich_text": [{"text": {"content": body.get("Hashtags", "")}}]},
                    "Data de postagem": {"date": {"start": body.get("Data de postagem")}}
                }
            }
        )
        return {"status": "success", "details": "Post atualizado", "notion_response": response.json()}
    except Exception as e:
        return {"status": "error", "details": str(e)}


@app.patch("/notion/post/{page_id}/status")
def update_post_status(page_id: str, body: dict):
    try:
        status = body.get("status")
        with open("tokens.json", "r") as file:
            tokens = json.load(file)
        token = list(tokens.values())[0]["access_token"]

        response = requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            },
            json={
                "properties": {
                    "Status": {"select": {"name": status}}
                }
            }
        )
        return {"status": "success", "details": "Status atualizado", "notion_response": response.json()}
    except Exception as e:
        return {"status": "error", "details": str(e)}


@app.delete("/notion/post/{page_id}")
def delete_post_by_id(page_id: str):
    try:
        with open("tokens.json", "r") as file:
            tokens = json.load(file)
        token = list(tokens.values())[0]["access_token"]

        response = requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            },
            json={"archived": True}
        )
        return {"status": "success", "details": "Post arquivado com sucesso", "notion_response": response.json()}
    except Exception as e:
        return {"status": "error", "details": str(e)}


@app.patch("/notion/post/{page_id}/content")
def update_post_content(page_id: str, body: dict):
    description = body.get("description", "").strip()
    if not description:
        return {"status": "error", "details": "Descrição vazia"}

    try:
        with open("tokens.json", "r") as file:
            tokens = json.load(file)
        token = list(tokens.values())[0]["access_token"]

        # Apaga blocos existentes
        delete_existing = requests.get(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28"
            }
        )
        children = delete_existing.json().get("results", [])
        for block in children:
            requests.patch(
                f"https://api.notion.com/v1/blocks/{block['id']}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json"
                },
                json={"archived": True}
            )

        # Adiciona novo bloco
        response = requests.patch(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            },
            json={
                "children": [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": description
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        )

        if response.status_code == 200:
            return {"status": "success", "details": "Conteúdo atualizado com sucesso"}
        else:
            return {"status": "error", "details": response.json()}

    except Exception as e:
        return {"status": "error", "details": str(e)}
@app.get("/routes")
def list_routes():
    return [route.path for route in app.routes]