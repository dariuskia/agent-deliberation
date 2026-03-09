import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4

import yaml
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from deliberation.llm import LLMClient
from deliberation.models import Principal

from .schemas import LaunchRequest, LaunchResponse, RunSummary
from .streaming import run_deliberation_streaming

BASE_DIR = Path(__file__).resolve().parent.parent
RUNS_DIR = BASE_DIR / "runs"

load_dotenv(BASE_DIR / ".env")

app = FastAPI(title="Deliberation Viewer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session queues for live streaming
sessions: dict[str, asyncio.Queue] = {}


def _load_config():
    with open(BASE_DIR / "config.yaml") as f:
        return yaml.safe_load(f)


def _load_principals(config, filter_ids: list[str] | None = None) -> list[Principal]:
    with open(BASE_DIR / config["principals_file"]) as f:
        all_principals = [Principal(**p) for p in yaml.safe_load(f)]
    selected_ids = filter_ids or config["deliberation"].get("principal_ids")
    if selected_ids:
        return [p for p in all_principals if p.id in selected_ids]
    return all_principals


# --- Replay endpoints ---


@app.get("/api/runs", response_model=list[RunSummary])
async def list_runs():
    runs = []
    if not RUNS_DIR.exists():
        return runs
    for path in sorted(RUNS_DIR.glob("*_result.json"), reverse=True):
        with open(path) as f:
            data = json.load(f)
        stem = path.stem  # e.g. 20260226_120444_result
        timestamp = stem.replace("_result", "")
        runs.append(RunSummary(id=stem, timestamp=timestamp, question=data["question"]))
    return runs


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    path = RUNS_DIR / f"{run_id}.json"
    if not path.exists():
        return {"error": "not found"}
    with open(path) as f:
        return json.load(f)


@app.get("/api/config")
async def get_config():
    config = _load_config()
    principals = _load_principals(config)
    return {
        "question": config["question"],
        "model": config["llm"]["model"],
        "num_rounds": config["deliberation"]["num_rounds"],
        "principals": [
            {"id": p.id, "name": p.name, "profile": p.profile, "values": p.values, "hidden_values": p.hidden_values}
            for p in principals
        ],
    }


# --- Live deliberation endpoints ---


@app.post("/api/deliberate", response_model=LaunchResponse)
async def start_deliberation(req: LaunchRequest, background_tasks: BackgroundTasks):
    config = _load_config()
    principals = _load_principals(config, filter_ids=req.principal_ids)

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    llm = LLMClient(
        api_key=api_key,
        model=config["llm"]["model"],
        base_url=config["llm"]["base_url"],
    )

    question = req.question or config["question"]
    num_rounds = req.num_rounds or config["deliberation"]["num_rounds"]

    session_id = str(uuid4())
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    sessions[session_id] = queue

    background_tasks.add_task(
        run_deliberation_streaming,
        llm=llm,
        principals=principals,
        question=question,
        num_rounds=num_rounds,
        event_queue=queue,
        runs_dir=RUNS_DIR,
    )

    return LaunchResponse(
        session_id=session_id,
        stream_url=f"/api/deliberate/{session_id}/stream",
    )


@app.get("/api/deliberate/{session_id}/stream")
async def stream_deliberation(session_id: str):
    queue = sessions.get(session_id)

    async def event_generator():
        if queue is None:
            yield {"event": "error", "data": json.dumps({"message": "session not found"})}
            return
        try:
            while True:
                event = await queue.get()
                yield {"event": event["type"], "data": json.dumps(event["data"])}
                if event["type"] in ("done", "error"):
                    break
        finally:
            sessions.pop(session_id, None)

    return EventSourceResponse(event_generator())
