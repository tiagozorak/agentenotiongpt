import json
import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()
notion = Client(auth=os.getenv("NOTION_TOKEN"))
database_id = os.getenv("NOTION_DATABASE_ID")

def main():
    json_input = input("📄 Cole o JSON para listar ideias:\n").strip()
    try:
        dados = json.loads(json_input)
        filtros = dados.get("filter_by", {})
        status = filtros.get("status")
        tipo = filtros.get("type")

        filtro = {"and": []}
        if status:
            filtro["and"].append({"property": "Status", "select": {"equals": status}})
        if tipo:
            filtro["and"].append({"property": "Tipo de post", "select": {"equals": tipo}})

        query = notion.databases.query(database_id=database_id, filter=filtro)
        resultados = query.get("results", [])

        if not resultados:
            print("⚠️ Nenhum card encontrado com esses filtros.")
            return

        print(f"📋 {len(resultados)} ideias encontradas:")
        for item in resultados:
            titulo = item["properties"]["Nome"]["title"][0]["text"]["content"]
            print(f"→ {titulo}")
    except Exception as e:
        print("❌ Erro:", e)

if __name__ == "__main__":
    main()
