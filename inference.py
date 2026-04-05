"""
Inference Script — SQL Query Grader OpenEnv
============================================
Runs a language model against all 3 tasks via the OpenAI client.

Environment variables:
  API_BASE_URL  — LLM endpoint (default: HuggingFace router)
  MODEL_NAME    — model identifier (default: Qwen/Qwen2.5-72B-Instruct)
  HF_TOKEN      — your HuggingFace API key (required, no default)
"""

import os
import sys
import json
import time
from openai import OpenAI

# ── Credentials (required by checklist) ──────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN     = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    print("ERROR: Set HF_TOKEN environment variable.")
    sys.exit(1)

# ── Environment (direct import — no HTTP needed) ──────────────────────────────
from env.environment import SQLQueryEnv
from env.models import SQLAction

# ── Config ────────────────────────────────────────────────────────────────────
MAX_STEPS   = 3
TEMPERATURE = 0.1
MAX_TOKENS  = 400
TASKS       = ["task_easy", "task_medium", "task_hard"]

SYSTEM_PROMPT = """You are an expert SQL analyst.
Your job is to write a single, correct SQL SELECT query that answers the given question.

Rules:
- Output ONLY the raw SQL query — no explanations, no markdown fences, no comments.
- Use only standard SQL compatible with SQLite.
- Do not use CREATE, INSERT, UPDATE, DELETE — only SELECT.
- If you made an error in a previous attempt, carefully fix it.
"""


def build_user_prompt(task_info, attempt, last_sql, last_error, last_reward):
    prompt = f"""Database schema:
{task_info['schema_description']}

Question:
{task_info['question']}

Hint:
{task_info['hint']}
"""
    if attempt > 1 and last_sql:
        prompt += f"\n--- Your previous attempt (attempt {attempt - 1}) ---\n{last_sql}\n"
        if last_error:
            prompt += f"Error: {last_error}\n"
        if last_reward is not None:
            prompt += f"Score so far: {last_reward:.4f} / 1.0\n"
        prompt += "\nPlease fix your query and try again.\n"

    prompt += "\nWrite the correct SQL query:"
    return prompt


def run_task(client, env, task_id):
    obs = env.reset(task_id=task_id)

    # ── START log (required structured format) ────────────────────────────────
    print(json.dumps({
        "type": "START",
        "task_id": task_id,
        "difficulty": obs.difficulty,
        "question": obs.question,
    }))

    best_score = 0.0
    final_reward = None

    for attempt in range(1, MAX_STEPS + 1):

        user_prompt = build_user_prompt(
            task_info={
                "schema_description": obs.schema_description,
                "question": obs.question,
                "hint": obs.hint,
            },
            attempt=attempt,
            last_sql=obs.last_sql,
            last_error=obs.last_error,
            last_reward=obs.last_reward,
        )

        # ── LLM call via OpenAI client (required by checklist) ────────────────
        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            sql = completion.choices[0].message.content.strip()
            # Strip markdown fences if model added them
            if sql.startswith("```"):
                lines = sql.split("\n")
                sql = "\n".join(l for l in lines if not l.startswith("```")).strip()
        except Exception as e:
            sql = "SELECT 1"

        # Submit to environment
        obs, reward, done = env.step(SQLAction(sql=sql))
        best_score = max(best_score, reward.total)
        final_reward = reward

        # ── STEP log (required structured format) ─────────────────────────────
        print(json.dumps({
            "type": "STEP",
            "task_id": task_id,
            "attempt": attempt,
            "sql": sql[:200],
            "score": reward.total,
            "syntax_valid": reward.syntax_valid,
            "columns_correct": reward.columns_correct,
            "exact_match": reward.exact_match,
            "error": reward.error_message,
        }))

        if done:
            break

        time.sleep(0.5)

    # ── END log (required structured format) ──────────────────────────────────
    print(json.dumps({
        "type": "END",
        "task_id": task_id,
        "difficulty": obs.difficulty,
        "best_score": round(best_score, 4),
        "exact_match": final_reward.exact_match if final_reward else False,
        "attempts_used": attempt,
    }))

    return {
        "task_id": task_id,
        "difficulty": obs.difficulty,
        "best_score": round(best_score, 4),
        "exact_match": final_reward.exact_match if final_reward else False,
        "attempts_used": attempt,
    }


def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
    env    = SQLQueryEnv()

    results = []
    total_start = time.time()

    for task_id in TASKS:
        result = run_task(client, env, task_id)
        results.append(result)

    env.close()
    elapsed = time.time() - total_start

    avg = sum(r["best_score"] for r in results) / len(results)

    # Final summary
    print(json.dumps({
        "type": "SUMMARY",
        "model": MODEL_NAME,
        "results": results,
        "average_score": round(avg, 4),
        "runtime_seconds": round(elapsed, 1),
    }))

    # Save scores file
    with open("baseline_scores.json", "w") as f:
        json.dump({
            "model": MODEL_NAME,
            "results": results,
            "average_score": round(avg, 4),
            "runtime_seconds": round(elapsed, 1),
        }, f, indent=2)


if __name__ == "__main__":
    main()