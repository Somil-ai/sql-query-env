---
title: SQL Query Grader
emoji: 🗄️
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
tags:
  - openenv
---

# SQL Query Grader — OpenEnv Environment

An OpenEnv environment where an AI agent writes SQL queries to answer data analysis questions.
The environment runs queries against an in-memory SQLite database and grades results with partial credit.

---

## Motivation

SQL query writing is one of the most common real-world tasks for data analysts, engineers, and students.
Unlike toy environments, this one tests a skill that directly maps to production work:
given a schema and a business question, produce a correct SQL query.

Grading is fully deterministic — there is no ambiguity in whether a query returns the right rows.
Partial credit signals let an RL agent learn incrementally (syntax → structure → correctness).

---

## Action Space

```json
{
  "sql": "<string — a SQL SELECT query>"
}
```

The agent submits a single SQL string at each step. Only SELECT statements are permitted.

---

## Observation Space

```json
{
  "task_id":            "<string>",
  "difficulty":         "easy | medium | hard",
  "schema_description": "<string — human-readable table/column definitions>",
  "question":           "<string — natural language question>",
  "hint":               "<string — guidance hint>",
  "last_sql":           "<string | null — agent's previous query>",
  "last_error":         "<string | null — SQL error from last step>",
  "last_reward":        "<float | null — score from last step>",
  "done":               "<bool>"
}
```

---

## Reward Function

Partial credit is awarded at each step (scores 0.0-1.0):

| Component | Weight | Criteria |
|---|---|---|
| Syntax valid | +0.10 | SQL parses and executes without error |
| Columns correct | +0.20 | Returned columns match expected column names |
| Row count score | +0.10-0.20 | Partial credit proportional to row count closeness |
| Category/value match | +0.30 | Correct values returned (task-dependent) |
| Exact match | +0.50 | Result rows exactly match expected answer |

The reward is never binary — an agent always gets signal even for partially correct queries.

---

## Tasks

### Task 1 — Easy (task_easy)

**Question:** Return first_name, last_name, email of all customers in California, ordered by last_name ascending.

**Expected difficulty:** A capable model should score 0.85-1.0.

**Key skills tested:** WHERE filter, ORDER BY, column selection.

---

### Task 2 — Medium (task_medium)

**Question:** Find the top 3 product categories by total revenue (price x quantity) in 2023. Return category and total_revenue ordered by revenue descending.

**Expected difficulty:** A capable model should score 0.60-0.80.

**Key skills tested:** JOIN, GROUP BY, aggregate functions (SUM), ORDER BY, LIMIT, date filtering.

---

### Task 3 — Hard (task_hard)

**Question:** Compute the 7-day retention rate for each user signup cohort. Return cohort_date, total_users, retained_users, retention_rate.

**Expected difficulty:** A capable model should score 0.30-0.60.

**Key skills tested:** CTEs or subqueries, LEFT JOIN, COUNT DISTINCT, date arithmetic.

---

## Setup and Usage

### Local (without Docker)

```bash
git clone https://huggingface.co/spaces/somil1064/sql-query-grader
cd sql-query-grader
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --reload --port 7860
```

Then open: http://localhost:7860/docs

### With Docker

```bash
docker build -t sql-query-grader .
docker run -p 7860:7860 sql-query-grader
```

### Run the inference script

```bash
export HF_TOKEN=your_token_here
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
export API_BASE_URL=https://router.huggingface.co/v1
python inference.py
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | /health | Health check |
| GET | /tasks | List all tasks |
| POST | /reset | Start a new episode |
| POST | /step | Submit a SQL query |
| GET | /state | Current episode state |
| GET | /docs | Interactive API explorer |

---

## Baseline Scores

Measured with Qwen/Qwen2.5-72B-Instruct via HuggingFace router:

| Task | Difficulty | Score |
|---|---|---|
| task_easy | easy | 1.0000 |
| task_medium | medium | 1.0000 |
| task_hard | hard | 0.6000 |
| Average | | 0.8667 |

---

## Environment Variables

| Variable | Description |
|---|---|
| API_BASE_URL | LLM API endpoint |
| MODEL_NAME | Model identifier |
| HF_TOKEN | HuggingFace API key |