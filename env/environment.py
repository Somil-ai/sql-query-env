"""
Core OpenEnv environment: SQLQueryEnv.
Implements the standard step() / reset() / state() API.
"""

import sqlite3
from typing import Tuple, Optional

from env.models import SQLObservation, SQLAction, SQLReward, EpisodeState
from env.database import create_connection, SCHEMA_DESCRIPTION
from env.tasks import ALL_TASKS


class SQLQueryEnv:
    """
    An environment where an AI agent must write SQL queries to answer
    data analysis questions against an in-memory SQLite database.
    """

    MAX_STEPS = 5  # Agent gets 5 attempts per task

    def __init__(self):
        self._conn: Optional[sqlite3.Connection] = None
        self._task_id: Optional[str] = None
        self._step_count: int = 0
        self._done: bool = False
        self._last_sql: Optional[str] = None
        self._last_reward: float = 0.0
        self._last_error: Optional[str] = None

    # ------------------------------------------------------------------
    # Public OpenEnv API
    # ------------------------------------------------------------------

    def reset(self, task_id: str = "task_easy") -> SQLObservation:
        """
        Start a fresh episode for the given task.
        Creates a new database connection and resets all state.
        """
        if task_id not in ALL_TASKS:
            raise ValueError(
                f"Unknown task '{task_id}'. "
                f"Valid options: {list(ALL_TASKS.keys())}"
            )

        # Fresh database for every episode (no state leaks between runs)
        self._conn = create_connection()
        self._task_id = task_id
        self._step_count = 0
        self._done = False
        self._last_sql = None
        self._last_reward = 0.0
        self._last_error = None

        task_meta, _ = ALL_TASKS[task_id]
        return SQLObservation(
            task_id=task_id,
            difficulty=task_meta["difficulty"],
            schema_description=SCHEMA_DESCRIPTION,
            question=task_meta["question"],
            hint=task_meta["hint"],
            last_sql=None,
            last_error=None,
            last_reward=None,
            done=False,
        )

    def step(self, action: SQLAction) -> Tuple[SQLObservation, SQLReward, bool]:
        """
        Execute the agent's SQL query and return (observation, reward, done).

        Rewards partial credit at each step. Episode ends when:
        - The agent achieves exact_match (score = 1.0), OR
        - MAX_STEPS attempts have been used.
        """
        if self._done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")
        if self._conn is None:
            raise RuntimeError("Environment not initialised. Call reset() first.")

        self._step_count += 1
        task_meta, grader = ALL_TASKS[self._task_id]

        # Run the grader
        reward = grader(self._conn, action.sql)
        self._last_sql = action.sql
        self._last_reward = reward.total
        self._last_error = reward.error_message

        # Episode ends on exact match or max steps
        if reward.exact_match or self._step_count >= self.MAX_STEPS:
            self._done = True

        obs = SQLObservation(
            task_id=self._task_id,
            difficulty=task_meta["difficulty"],
            schema_description=SCHEMA_DESCRIPTION,
            question=task_meta["question"],
            hint=task_meta["hint"],
            last_sql=action.sql,
            last_error=reward.error_message,
            last_reward=reward.total,
            done=self._done,
        )
        return obs, reward, self._done

    def state(self) -> EpisodeState:
        """Return the current internal state (for debugging / logging)."""
        return EpisodeState(
            task_id=self._task_id or "none",
            difficulty=ALL_TASKS[self._task_id][0]["difficulty"] if self._task_id else "none",
            step_count=self._step_count,
            current_reward=self._last_reward,
            done=self._done,
            last_sql=self._last_sql,
        )

    def close(self):
        """Release the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None