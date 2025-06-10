from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from notion_client import Client
import os

app = FastAPI()

# Configura o cliente Notion com a variável de ambiente
notion = Client(
    auth=os.getenv("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"),
    notion_version="2022-06-28"
)

class PageTitle(BaseModel):
    title: str

@app.get("/")
async def root():
    return {"message": "Agent GPT is running successfully on Render!"}

@app.get("/test-notion")
async def test_notion():
    try:
        response = notion.search(filter={"property": "object", "value": "page"})
        return {"status": "success", "pages_found": len(response.get("results", []))}
    except Exception as e:
        return {"status": "error", "details": str(e)}

@app.post("/create-page")
async def create_page(payload: PageTitle):
    try:
        database_id = os.getenv("2062b8686ff281cfb7f5e379236da5cf")
        if not database_id:
            raise HTTPException(status_code=500, detail="DATABASE_ID not set in environment variables")

        response = notion.pages.create(
            parent={"database_id": database_id},
            properties={
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": payload.title
                            }
                        }
                    ]
                }
            }
        )
        return {"status": "success", "page_id": response["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
