import os
import json
from notion_client import Client
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

notion = Client(auth=os.getenv("NOTION_TOKEN"))
database_id = os.getenv("NOTION_DATABASE_ID")

def find_page_id_by_title(database_id, title):
    response = notion.databases.query(
        database_id=database_id,
        filter={
            "property": "Nome",
            "title": {
                "equals": title
            }
        }
    )
    results = response.get("results", [])
    return results[0]["id"] if results else None

def update_page_properties(page_id, updates):
    props = {}

    if "title" in updates:
        props["Nome"] = {
            "title": [{"text": {"content": updates["title"]}}]
        }
    if "status" in updates:
        props["Status"] = {
            "select": {"name": updates["status"]}
        }
    if "type" in updates:
        props["Tipo de post"] = {
            "select": {"name": updates["type"]}
        }
    if "hashtags" in updates:
        props["Hashtags"] = {
            "rich_text": [{"text": {"content": updates["hashtags"]}}]
        }
    if "date" in updates:
        props["Data de postagem"] = {
            "date": {"start": updates["date"]}
        }

    # Atualiza propriedades principais
    notion.pages.update(page_id=page_id, properties=props)

    # Atualiza o corpo do card (bloco de parágrafo)
    if "description" in updates:
        notion.blocks.children.append(
            block_id=page_id,
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": updates["description"]}}
                        ]
                    }
                }
            ]
        )

if __name__ == "__main__":
    print("🧾 Cole aqui o JSON de atualização:")
    entrada = input()
    try:
        dados = json.loads(entrada)
        if dados.get("action") != "update_post":
            print("❌ Ação inválida.")
            exit()

        titulo = dados.get("title")
        atualizacoes = dados.get("updates", {})
        if not titulo or not atualizacoes:
            print("❌ JSON incompleto. Inclua 'title' e 'updates'.")
            exit()

        page_id = find_page_id_by_title(database_id, titulo)
        if not page_id:
            print("❌ Nenhum card encontrado com esse título.")
        else:
            update_page_properties(page_id, atualizacoes)
            print("✅ Card atualizado com sucesso!")

    except json.JSONDecodeError:
        print("❌ Erro: o conteúdo não está em formato JSON válido.")