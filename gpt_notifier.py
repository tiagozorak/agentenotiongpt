import os
import json
from dotenv import load_dotenv
from notion_client import Client

# Carrega variáveis
load_dotenv()
notion = Client(auth=os.getenv("NOTION_TOKEN"))
database_id = os.getenv("NOTION_DATABASE_ID")

def criar_ideia(titulo, status="💡 Ideias para Post"):
    try:
        notion.pages.create(
            parent={"database_id": database_id},
            properties={
                "Nome": {"title": [{"text": {"content": titulo}}]},
                "Status": {"select": {"name": status}}
            }
        )
        print(f"✅ Criado: {titulo}")
    except Exception as e:
        print("❌ Erro:", e)

def processar_instrucao(data):
    if data["action"] == "create_post_idea":
        criar_ideia(data["title"], data.get("status", "💡 Ideias para Post"))
    else:
        print("❌ Ação desconhecida.")

# 👇 Simulador: cole aqui o JSON gerado pelo agente
if __name__ == "__main__":
    exemplo_json = '''
    {
        "action": "create_post_idea",
        "title": "3 erros comuns ao usar hashtags no Instagram",
        "status": "💡 Ideias para Post"
    }
    '''
    instrucoes = json.loads(exemplo_json)
    processar_instrucao(instrucoes)
