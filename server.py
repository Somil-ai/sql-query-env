"""
FastAPI server exposing the OpenEnv HTTP API.
Endpoints: POST /reset  POST /step  GET /state  GET /health  GET /tasks
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from env.environment import SQLQueryEnv
from env.models import SQLObservation, SQLAction, SQLReward, EpisodeState

app = FastAPI(
    title="SQL Query Grader — OpenEnv",
    description=(
        "An OpenEnv environment where an AI agent writes SQL queries "
        "to answer data analysis questions. Graded with partial credit."
    ),
    version="1.0.0",
)

# One shared environment instance (single-user; fine for HF Spaces eval)
_env = SQLQueryEnv()


# ------------------------------------------------------------------
# Request / Response schemas
# ------------------------------------------------------------------

class ResetRequest(BaseModel):
    task_id: str = "task_easy"


class StepRequest(BaseModel):
    sql: str


class StepResponse(BaseModel):
    observation: SQLObservation
    reward: SQLReward
    done: bool


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@app.get("/health")
def health():
    """Ping endpoint — must return 200 for HF Space validation."""
    return {"status": "ok", "environment": "sql-query-grader", "version": "1.0.0"}


@app.get("/tasks")
def list_tasks():
    """List all available tasks with metadata."""
    return {
        "tasks": [
            {
                "task_id": "task_easy",
                "difficulty": "easy",
                "description": "Return all customers from California sorted by last name",
            },
            {
                "task_id": "task_medium",
                "difficulty": "medium",
                "description": "Find top 3 product categories by total revenue in 2023",
            },
            {
                "task_id": "task_hard",
                "difficulty": "hard",
                "description": "Compute 7-day retention rate per user signup cohort",
            },
        ]
    }


@app.post("/reset", response_model=SQLObservation)
def reset(request: ResetRequest):
    """
    Start a new episode. Returns the initial observation with
    database schema, the question, and a helpful hint.
    """
    try:
        obs = _env.reset(task_id=request.task_id)
        return obs
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step", response_model=StepResponse)
def step(request: StepRequest):
    """
    Submit a SQL query. Returns the observation, a detailed reward
    breakdown, and whether the episode is done.
    """
    try:
        action = SQLAction(sql=request.sql)
        obs, reward, done = _env.step(action)
        return StepResponse(observation=obs, reward=reward, done=done)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@app.get("/state", response_model=EpisodeState)
def state():
    """Return the current internal environment state (for debugging)."""
    return _env.state()


# ------------------------------------------------------------------
# Root redirect to docs
# ------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "SQL Query Grader OpenEnv — visit /docs for interactive API",
        "endpoints": ["/reset", "/step", "/state", "/tasks", "/health"],
    }