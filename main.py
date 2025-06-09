from fastapi import FastAPI
import os
import sys
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

@app.get("/")
async def root():
    # Debug: log ambiente Python e sys.path
    return {
        "message": "Agent GPT is running successfully on Render!",
        "sys_executable": sys.executable,
        "sys_path": sys.path,
        "env_PORT": os.getenv("PORT")
    }
