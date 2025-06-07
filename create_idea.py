import os
import json
from notion_client import Client
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()
notion = Client(auth=os.getenv("NOTION_TOKEN"))
database_id = os.getenv("NOTION_DATABASE_ID")

print("🧾 Cole aqui o JSON de criação de ideia:")
user_input = input()

try:
    data = json.loads(user_input)
except json.JSONDecodeError:
    print("❌ Erro: o conteúdo não está em formato JSON válido.")
    exit()

# Extração dos campos
title = data.get("title", "🧠 Ideia sem título")
status = data.get("status", "💡 Ideias para Post")
description = data.get("description", "")
post_type = data.get("post_type", "")
post_date = data.get("post_date", "")  # Formato: YYYY-MM-DD
hashtags = data.get("hashtags", "")  # Como texto livre

# Montagem das propriedades
properties = {
    "Nome": {
        "title": [{"text": {"content": title}}]
    },
    "Status": {
        "select": {"name": status}
    },
    "Tipo de post": {
        "select": {"name": post_type}
    }
}

# Campos opcionais
if post_date:
    properties["Data de postagem"] = {"date": {"start": post_date}}

if hashtags:
    properties["Hashtags"] = {
        "rich_text": [{"type": "text", "text": {"content": hashtags}}]
    }

# Envio para o Notion
try:
    notion.pages.create(
        parent={"database_id": database_id},
        properties=properties,
        children=[
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": description}}]
                }
            }
        ]
    )
    print("✅ Card criado com sucesso!")
except Exception as e:
    print(f"❌ Erro ao criar card: {e}")
