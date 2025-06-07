import os
from dotenv import load_dotenv
from notion_client import Client

# Carrega as variáveis do arquivo .env
load_dotenv()

# Lê as credenciais
notion_token = os.getenv("NOTION_TOKEN")
database_id = os.getenv("NOTION_DATABASE_ID")

# Inicializa o cliente do Notion
notion = Client(auth=notion_token)

# Testa a leitura da base de dados
try:
    response = notion.databases.query(database_id=database_id)

    print("\n🧠 Dados retornados da base do Notion:")
    for result in response["results"]:
        props = result["properties"]
        title = props.get("Nome") or props.get("Name") or props.get("Título") or {}
        text = title.get("title", [])
        if text:
            print("→", text[0]["plain_text"])
        else:
            print("→ (sem título encontrado)")

except Exception as e:
    print("\n❌ Erro ao acessar o Notion:")
    print(e)
