from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from notion_client import Client
import os

app = FastAPI()

# Inicializa o cliente da API do Notion
notion = Client(auth=os.getenv("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"))
DATABASE_ID = os.getenv("2062b8686ff281cfb7f5e379236da5cf")

# Modelos de entrada
class PostCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "A fazer"

class PostUpdate(BaseModel):
    page_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class PostDelete(BaseModel):
    page_id: str

@app.post("/create_post")
async def create_post(post: PostCreate):
    try:
        new_page = notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties={
                "Título": {
                    "title": [{"text": {"content": post.title}}]
                },
                "Status": {
                    "select": {"name": post.status}
                }
            },
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": post.description or ""}}
                        ]
                    }
                }
            ]
        )
        return {"message": "Post criado com sucesso", "page_id": new_page["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/update_post")
async def update_post(update: PostUpdate):
    try:
        props = {}
        if update.title:
            props["Título"] = {"title": [{"text": {"content": update.title}}]}
        if update.status:
            props["Status"] = {"select": {"name": update.status}}

        if props:
            notion.pages.update(page_id=update.page_id, properties=props)

        if update.description is not None:
            # Remove todos os blocos existentes e adiciona o novo conteúdo
            blocks = notion.blocks.children.list(update.page_id)["results"]
            for block in blocks:
                notion.blocks.delete(block["id"])
            notion.blocks.children.append(
                update.page_id,
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {"type": "text", "text": {"content": update.description}}
                            ]
                        }
                    }
                ]
            )

        return {"message": "Post atualizado com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/list_posts")
async def list_posts():
    try:
        response = notion.databases.query(database_id=DATABASE_ID)
        posts = []
        for result in response["results"]:
            props = result["properties"]
            posts.append({
                "page_id": result["id"],
                "title": props["Título"]["title"][0]["text"]["content"] if props["Título"]["title"] else "",
                "status": props["Status"]["select"]["name"] if props["Status"]["select"] else ""
            })
        return posts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete_post")
async def delete_post(data: PostDelete):
    try:
        notion.blocks.delete(block_id=data.page_id)
        return {"message": "Post excluído com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/debug_token")
def debug_token():
    from os import getenv
    token = getenv("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")
    return {
        "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": token[:8] + "..." if token else None,
        "env_var_exists": token is not None
    }
