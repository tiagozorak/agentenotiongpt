from fastapi import APIRouter

router = APIRouter()

@router.post("/create_post")
def create_post(data: dict):
    return {"status": "Post created", "data": data}

@router.patch("/update_post")
def update_post(data: dict):
    return {"status": "Post updated", "data": data}

@router.delete("/delete_post")
def delete_post(data: dict):
    return {"status": "Post deleted", "data": data}

@router.get("/list_status")
def list_status():
    return {"statuses": ["Ideia", "Em produção", "Revisão", "Publicado"]}
