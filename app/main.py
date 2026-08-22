from fastapi import FastAPI
from typing import Dict

app = FastAPI(title="Manak Sahayak")

@app.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}
