"""
Inference Script — SQL Query Grader OpenEnv
============================================
Runs a language model against all 3 tasks via the OpenAI client.
Reads credentials from environment variables:
  API_BASE_URL  — LLM endpoint (default: HuggingFace router)
  MODEL_NAME    — model identifier
  HF_TOKEN      — your HuggingFace API key

Usage:
  python inference.py

Runtime: ~2–5 minutes on 2 vCPU (well under the 20-min limit).
"""

import os
import sys
import json
import time
from openai import OpenAI

# ── Credentials ──────────────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
MODEL_NAME   = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

if not API_KEY:
    print("ERROR: Set HF_TOKEN or API_KEY environment variable.")
    sys.exit(1)

# ── Environment (import directly — no HTTP needed for inference.py) ───────────
from env.environment import SQLQueryEnv
from env.models import SQLAction

# ── Config ───────────────────────────────────────────────────────────────────
MAX_STEPS   = 3        # Agent gets 3 attempts per task
TEMPERATURE = 0.1      # Low temp for deterministic SQL generation
MAX_TOKENS  = 400

TASKS = ["task_easy", "task_medium", "task_hard"]

SYSTEM_PROMPT = """You are an expert SQL analyst. 
Your job is to write a single, correct SQL SELECT query that answers the given question.

Rules:
- Output ONLY the raw SQL query — no explanations, no markdown fences, no comments.
- Use only standard SQL compatible with SQLite.
- Do not use CREATE, INSERT, UPDATE, DELETE — only SELECT.
- If you made an error in a previous attempt, carefully fix it.
"""


def build_user_prompt(task_info: dict, attempt: int, last_sql: str | None, last_error: str | None, last_reward: float | None) -> str:
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


def run_task(client: OpenAI, env: SQLQueryEnv, task_id: str) -> dict:
    print(f"\n{'='*60}")
    print(f"  Task: {task_id}")
    print(f"{'='*60}")

    obs = env.reset(task_id=task_id)
    print(f"  Difficulty : {obs.difficulty}")
    print(f"  Question   : {obs.question[:80]}...")

    best_score = 0.0
    final_reward = None

    for attempt in range(1, MAX_STEPS + 1):
        print(f"\n  [Attempt {attempt}/{MAX_STEPS}]")

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

        # Call LLM via OpenAI client
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
            # Strip markdown fences if model added them anyway
            if sql.startswith("```"):
                lines = sql.split("\n")
                sql = "\n".join(
                    l for l in lines
                    if not l.startswith("```")
                ).strip()
        except Exception as e:
            print(f"  LLM call failed: {e}")
            sql = "SELECT 1"

        print(f"  SQL: {sql[:120]}{'...' if len(sql) > 120 else ''}")

        # Submit to environment
        obs, reward, done = env.step(SQLAction(sql=sql))

        print(f"  Score     : {reward.total:.4f}")
        print(f"  Syntax OK : {reward.syntax_valid}")
        print(f"  Cols OK   : {reward.columns_correct}")
        print(f"  Exact     : {reward.exact_match}")
        if reward.error_message:
            print(f"  Error     : {reward.error_message}")

        best_score = max(best_score, reward.total)
        final_reward = reward

        if done:
            if reward.exact_match:
                print(f"\n  ✓ Exact match achieved on attempt {attempt}!")
            else:
                print(f"\n  ✗ Max attempts reached.")
            break

        time.sleep(0.5)  # Be polite to the API

    return {
        "task_id": task_id,
        "difficulty": obs.difficulty,
        "best_score": round(best_score, 4),
        "exact_match": final_reward.exact_match if final_reward else False,
        "attempts_used": attempt,
    }


def main():
    print("\nSQL Query Grader — OpenEnv Inference Script")
    print(f"Model      : {MODEL_NAME}")
    print(f"API URL    : {API_BASE_URL}")
    print(f"Max steps  : {MAX_STEPS} per task")

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    env    = SQLQueryEnv()

    results = []
    total_start = time.time()

    for task_id in TASKS:
        result = run_task(client, env, task_id)
        results.append(result)

    env.close()
    elapsed = time.time() - total_start

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  FINAL SCORES")
    print(f"{'='*60}")
    for r in results:
        status = "EXACT" if r["exact_match"] else f"partial"
        print(f"  {r['task_id']:<14} ({r['difficulty']:<6})  score={r['best_score']:.4f}  [{status}]")

    avg = sum(r["best_score"] for r in results) / len(results)
    print(f"\n  Average score : {avg:.4f}")
    print(f"  Total runtime : {elapsed:.1f}s")

    # Write JSON results for automated validation
    with open("baseline_scores.json", "w") as f:
        json.dump({
            "model": MODEL_NAME,
            "results": results,
            "average_score": round(avg, 4),
            "runtime_seconds": round(elapsed, 1),
        }, f, indent=2)
    print("\n  Results saved to baseline_scores.json")


if __name__ == "__main__":
    main()