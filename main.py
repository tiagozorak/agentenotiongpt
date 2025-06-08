from fastapi import FastAPI
from fastapi.responses import JSONResponse
from analyze_graphs import gerar_relatorio_kanban

app = FastAPI()

@app.get("/analyze-kanban")
def analyze_kanban():
    try:
        relatorio = gerar_relatorio_kanban()
        return JSONResponse(content={"success": True, "output": relatorio})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)})
if __name__ == "__main__":
    import uvicorn
    import os
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
  
