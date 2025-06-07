import requests

response = requests.get("http://127.0.0.1:8000/analyze-kanban")

if response.status_code == 200:
    print("✅ Sucesso! Resposta do servidor:")
    print(response.text)
else:
    print("❌ Falha:")
    print(response.status_code, response.text)
