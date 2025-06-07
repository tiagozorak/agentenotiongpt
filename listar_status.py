import os
from dotenv import load_dotenv
from notion_client import Client

# Carrega as variáveis do .env
load_dotenv()
notion = Client(auth=os.getenv("NOTION_TOKEN"))
database_id = os.getenv("NOTION_DATABASE_ID")

def listar_opcoes_status():
    try:
        db_info = notion.databases.retrieve(database_id=database_id)
        propriedades = db_info["properties"]

        if "Status" in propriedades:
            status_options = propriedades["Status"]["select"]["options"]
            print("📋 Opções válidas de 'Status':")
            for opt in status_options:
                print(f"→ '{opt['name']}' (ID: {opt['id']})")
        else:
            print("❌ A propriedade 'Status' não foi encontrada.")
    except Exception as e:
        print("❌ Erro ao buscar opções de 'Status':", e)

# Executar
listar_opcoes_status()
