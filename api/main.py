import json
import logging
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from common.models import PriceUpdate
from common.queue_adapter import QueueAdapter

app = FastAPI(title="PriceWatch API")
queue = QueueAdapter()


@app.exception_handler(RequestValidationError)
async def on_invalid(request, exc):
    reasons = [".".join(str(p) for p in e["loc"][1:]) + ": " + e["msg"] for e in exc.errors()]
    return JSONResponse(status_code=422, content={"error": "validation_failed", "reasons": reasons})


@app.post("/v1/prices", status_code=202)
def publish(update: PriceUpdate):
    message = update.model_dump(mode="json")
    message["received_at"] = datetime.now(timezone.utc).isoformat()
    try:
        queue.send(json.dumps(message))
    except Exception:
        logging.exception("queue publish failed")
        return JSONResponse(status_code=503, content={"error": "queue_unavailable"})
    return {"event_id": str(update.event_id), "status": "queued"}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
