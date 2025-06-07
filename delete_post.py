import json
import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()
notion = Client(auth=os.getenv("NOTION_TOKEN"))
database_id = os.getenv("NOTION_DATABASE_ID")

def buscar_id_por_titulo(titulo):
    query = notion.databases.query(database_id=database_id)
    for resultado in query.get("results"):
        props = resultado["properties"]
        if props.get("Nome", {}).get("title"):
            nome = props["Nome"]["title"][0]["text"]["content"]
            if nome == titulo:
                return resultado["id"]
    return None

def main():
    json_input = input("🗑️ Cole o JSON da exclusão:\n").strip()
    try:
        dados = json.loads(json_input)
        titulo = dados["title"]
        card_id = buscar_id_por_titulo(titulo)

        if not card_id:
            print("❌ Card não encontrado.")
            return

        notion.pages.update(page_id=card_id, archived=True)
        print("✅ Card arquivado com sucesso!")
    except Exception as e:
        print("❌ Erro:", e)

if __name__ == "__main__":
    main()
