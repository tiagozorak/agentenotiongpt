import os
from dotenv import load_dotenv
from notion_client import Client

# Carrega variáveis do .env
load_dotenv()
notion = Client(auth=os.getenv("NOTION_TOKEN"))
database_id = os.getenv("NOTION_DATABASE_ID")

db_info = notion.databases.retrieve(database_id=database_id)

print("📋 Propriedades disponíveis na base:")
for name in db_info["properties"]:
    print(f"→ {name}")
