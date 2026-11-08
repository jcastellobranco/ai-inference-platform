from fastapi import FastAPI

app = FastAPI(title="ATLAS Starter Service")


@app.get("/health/live")
def live():
    return {"status": "ok"}
