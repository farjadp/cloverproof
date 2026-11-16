"""FastAPI entry point. Run locally with `make dev`."""

from fastapi import FastAPI

app = FastAPI(title="CloverProof internal tool", version="0.0.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
