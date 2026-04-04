"""
Typed Pydantic models for the SQL Query Grader OpenEnv environment.
These define the observation, action, and reward contracts.
"""

from pydantic import BaseModel, Field
from typing import Optional


class SQLObservation(BaseModel):
    """What the agent sees at each step."""
    task_id: str = Field(description="Unique identifier for the current task")
    difficulty: str = Field(description="easy | medium | hard")
    schema_description: str = Field(description="Human-readable description of the database tables and columns")
    question: str = Field(description="Natural language question the agent must answer with SQL")
    hint: str = Field(description="A helpful hint to guide the agent")
    last_sql: Optional[str] = Field(default=None, description="The SQL the agent submitted last step (None on first step)")
    last_error: Optional[str] = Field(default=None, description="Error message if last SQL had a syntax error")
    last_reward: Optional[float] = Field(default=None, description="Reward from the last step")
    done: bool = Field(default=False, description="True when the episode is complete")


class SQLAction(BaseModel):
    """What the agent submits — a single SQL query string."""
    sql: str = Field(description="The SQL SELECT query to execute against the database")


class SQLReward(BaseModel):
    """Breakdown of the reward signal with partial credit components."""
    total: float = Field(ge=0.0, le=1.0, description="Final combined score (0.0–1.0)")
    syntax_valid: bool = Field(description="True if SQL parsed without error")
    columns_correct: bool = Field(description="True if returned columns match expected")
    row_count_score: float = Field(ge=0.0, le=1.0, description="Partial credit for row count closeness")
    exact_match: bool = Field(description="True if result rows exactly match expected answer")
    error_message: Optional[str] = Field(default=None, description="SQL execution error if any")


class EpisodeState(BaseModel):
    """Full internal state — returned by state() endpoint."""
    task_id: str
    difficulty: str
    step_count: int
    current_reward: float
    done: bool
    last_sql: Optional[str]