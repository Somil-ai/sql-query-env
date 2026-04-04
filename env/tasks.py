"""
Three graded tasks ranging from easy to hard.
Each task defines:
  - The natural language question
  - A hint
  - The expected answer rows
  - A grader function that returns a SQLReward
"""

import sqlite3
from typing import List, Tuple, Any

from env.models import SQLReward


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_sql(conn: sqlite3.Connection, sql: str) -> Tuple[bool, List[Any], str]:
    """
    Execute SQL. Returns (success, rows, error_message).
    Rows are lists of tuples with values lowercased/rounded for comparison.
    """
    try:
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        # Normalise: convert Row objects to plain tuples, lowercase strings
        normalised = []
        for row in rows:
            tup = tuple(
                v.strip().lower() if isinstance(v, str) else (round(v, 2) if isinstance(v, float) else v)
                for v in row
            )
            normalised.append(tup)
        return True, normalised, ""
    except Exception as e:
        return False, [], str(e)


def _columns_match(conn: sqlite3.Connection, sql: str, expected_cols: List[str]) -> bool:
    """Check that the query returns columns with the right names (case-insensitive)."""
    try:
        cursor = conn.execute(sql)
        actual_cols = [d[0].lower() for d in cursor.description or []]
        return sorted(actual_cols) == sorted([c.lower() for c in expected_cols])
    except Exception:
        return False


def _row_count_score(actual: int, expected: int) -> float:
    """Partial credit for row count closeness (1.0 = exact match)."""
    if expected == 0:
        return 1.0 if actual == 0 else 0.0
    ratio = actual / expected
    # Score decays as ratio moves away from 1.0
    if ratio == 1.0:
        return 1.0
    elif ratio > 1.0:
        return max(0.0, 1.0 - (ratio - 1.0))
    else:
        return ratio


# ---------------------------------------------------------------------------
# Task 1 — Easy
# ---------------------------------------------------------------------------

TASK_EASY = {
    "task_id": "task_easy",
    "difficulty": "easy",
    "question": (
        "Write a SQL query that returns the first_name, last_name, and email "
        "of all customers who live in California, ordered by last_name ascending."
    ),
    "hint": (
        "Use a WHERE clause to filter by state = 'California' "
        "and ORDER BY last_name ASC."
    ),
}

_TASK1_EXPECTED_COLS = ["first_name", "last_name", "email"]
_TASK1_EXPECTED_ROWS = {
    ("alice", "anderson", "alice@example.com"),
    ("carol", "clark", "carol@example.com"),
    ("eve", "evans", "eve@example.com"),
    ("frank", "foster", "frank@example.com"),
    ("henry", "hall", "henry@example.com"),
    ("jack", "jones", "jack@example.com"),
}


def grade_easy(conn: sqlite3.Connection, sql: str) -> SQLReward:
    score = 0.0

    # 1. Syntax valid (+0.1)
    ok, rows, error = _run_sql(conn, sql)
    if not ok:
        return SQLReward(
            total=0.0, syntax_valid=False, columns_correct=False,
            row_count_score=0.0, exact_match=False, error_message=error
        )
    score += 0.1

    # 2. Columns correct (+0.2)
    cols_ok = _columns_match(conn, sql, _TASK1_EXPECTED_COLS)
    if cols_ok:
        score += 0.2

    # 3. Row count score (+0.2)
    rc_score = _row_count_score(len(rows), len(_TASK1_EXPECTED_ROWS))
    score += 0.2 * rc_score

    # 4. Exact match (+0.5)
    exact = set(rows) == _TASK1_EXPECTED_ROWS
    if exact:
        score += 0.5

    return SQLReward(
        total=round(min(score, 1.0), 4),
        syntax_valid=True,
        columns_correct=cols_ok,
        row_count_score=round(rc_score, 4),
        exact_match=exact,
        error_message=None,
    )


# ---------------------------------------------------------------------------
# Task 2 — Medium
# ---------------------------------------------------------------------------

TASK_MEDIUM = {
    "task_id": "task_medium",
    "difficulty": "medium",
    "question": (
        "Write a SQL query that returns the top 3 product categories by total revenue "
        "in the year 2023. Revenue = SUM(products.price * orders.quantity). "
        "Return columns: category, total_revenue (rounded to 2 decimal places). "
        "Order by total_revenue descending."
    ),
    "hint": (
        "JOIN orders with products on product_id. "
        "Filter order_date starting with '2023'. "
        "GROUP BY category, ORDER BY total_revenue DESC, LIMIT 3."
    ),
}

# Electronics: Laptop(1200*7=8400) + Mouse(35*50=1750) + Monitor(650*16=10400) + Webcam(95*23=2185) = 22735
# Furniture:   Chair(450*13=5850) + Desk(800*5=4000) + Bookshelf(320*10=3200) = 13050
# Stationery:  Notebook(15*75=1125) + Pen(12*60=720) + Sticky(8*100=800) = 2645
# Computed from seed data:
_TASK2_EXPECTED_ROWS = {
    ("electronics",),
    ("furniture",),
    ("stationery",),
}
_TASK2_EXPECTED_COLS = ["category", "total_revenue"]


def _compute_expected_revenues(conn: sqlite3.Connection) -> dict:
    """Compute expected revenues from the actual data (ground truth)."""
    cursor = conn.execute("""
        SELECT p.category, ROUND(SUM(p.price * o.quantity), 2) as total_revenue
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.order_date LIKE '2023%'
        GROUP BY p.category
        ORDER BY total_revenue DESC
        LIMIT 3
    """)
    return {row[0].lower(): row[1] for row in cursor.fetchall()}


def grade_medium(conn: sqlite3.Connection, sql: str) -> SQLReward:
    score = 0.0
    expected_revenues = _compute_expected_revenues(conn)

    # 1. Syntax valid (+0.1)
    ok, rows, error = _run_sql(conn, sql)
    if not ok:
        return SQLReward(
            total=0.0, syntax_valid=False, columns_correct=False,
            row_count_score=0.0, exact_match=False, error_message=error
        )
    score += 0.1

    # 2. Columns correct (+0.2)
    cols_ok = _columns_match(conn, sql, _TASK2_EXPECTED_COLS)
    if cols_ok:
        score += 0.2

    # 3. Row count score (+0.1)
    rc_score = _row_count_score(len(rows), 3)
    score += 0.1 * rc_score

    # 4. Correct categories returned (+0.3)
    returned_categories = {r[0].lower() if r else "" for r in rows}
    expected_categories = set(expected_revenues.keys())
    category_overlap = len(returned_categories & expected_categories) / 3
    score += 0.3 * category_overlap

    # 5. Revenue values within 5% tolerance (+0.3)
    revenue_correct = 0
    for row in rows:
        if len(row) >= 2:
            cat = str(row[0]).lower()
            rev = row[1]
            if cat in expected_revenues and rev is not None:
                expected_rev = expected_revenues[cat]
                if expected_rev > 0 and abs(float(rev) - expected_rev) / expected_rev < 0.05:
                    revenue_correct += 1
    score += 0.3 * (revenue_correct / 3)

    exact = (returned_categories == expected_categories and revenue_correct == 3)

    return SQLReward(
        total=round(min(score, 1.0), 4),
        syntax_valid=True,
        columns_correct=cols_ok,
        row_count_score=round(rc_score, 4),
        exact_match=exact,
        error_message=None,
    )


# ---------------------------------------------------------------------------
# Task 3 — Hard
# ---------------------------------------------------------------------------

TASK_HARD = {
    "task_id": "task_hard",
    "difficulty": "hard",
    "question": (
        "Write a SQL query to compute the 7-day retention rate for each signup cohort. "
        "A cohort is defined by signup_date from the users table. "
        "A user is 'retained' in the 7-day window if they have a login event in user_events "
        "within 7 days of their signup_date (inclusive). "
        "Return columns: cohort_date, total_users, retained_users, retention_rate. "
        "retention_rate = ROUND(retained_users * 1.0 / total_users, 4). "
        "Order by cohort_date ascending."
    ),
    "hint": (
        "Use a CTE or subquery to count total users per signup_date. "
        "LEFT JOIN user_events on user_id where event_date <= DATE(signup_date, '+7 days'). "
        "COUNT(DISTINCT) retained users. "
        "SQLite date arithmetic: DATE(signup_date, '+7 days')."
    ),
}

_TASK3_EXPECTED_COLS = ["cohort_date", "total_users", "retained_users", "retention_rate"]


def _compute_expected_retention(conn: sqlite3.Connection) -> List[tuple]:
    cursor = conn.execute("""
        WITH cohorts AS (
            SELECT signup_date as cohort_date, COUNT(*) as total_users
            FROM users
            GROUP BY signup_date
        ),
        retained AS (
            SELECT u.signup_date as cohort_date,
                   COUNT(DISTINCT ue.user_id) as retained_users
            FROM users u
            LEFT JOIN user_events ue
                ON ue.user_id = u.id
               AND ue.event_date <= DATE(u.signup_date, '+7 days')
               AND ue.event_type = 'login'
            GROUP BY u.signup_date
        )
        SELECT c.cohort_date,
               c.total_users,
               COALESCE(r.retained_users, 0) as retained_users,
               ROUND(COALESCE(r.retained_users, 0) * 1.0 / c.total_users, 4) as retention_rate
        FROM cohorts c
        LEFT JOIN retained r ON c.cohort_date = r.cohort_date
        ORDER BY c.cohort_date
    """)
    return [tuple(row) for row in cursor.fetchall()]


def grade_hard(conn: sqlite3.Connection, sql: str) -> SQLReward:
    score = 0.0
    expected = _compute_expected_retention(conn)

    # 1. Syntax valid (+0.1)
    ok, rows, error = _run_sql(conn, sql)
    if not ok:
        return SQLReward(
            total=0.0, syntax_valid=False, columns_correct=False,
            row_count_score=0.0, exact_match=False, error_message=error
        )
    score += 0.1

    # 2. Columns correct (+0.2)
    cols_ok = _columns_match(conn, sql, _TASK3_EXPECTED_COLS)
    if cols_ok:
        score += 0.2

    # 3. Row count (+0.1)
    rc_score = _row_count_score(len(rows), len(expected))
    score += 0.1 * rc_score

    # 4. Cohort dates correct (+0.2)
    expected_dates = {str(r[0]).lower() for r in expected}
    returned_dates = {str(r[0]).lower() for r in rows if r} if rows else set()
    date_overlap = len(returned_dates & expected_dates) / max(len(expected_dates), 1)
    score += 0.2 * date_overlap

    # 5. Total_users counts correct (+0.1)
    expected_totals = {str(r[0]): r[1] for r in expected}
    total_correct = sum(
        1 for r in rows
        if len(r) >= 2 and str(r[0]) in expected_totals and r[1] == expected_totals[str(r[0])]
    )
    score += 0.1 * (total_correct / max(len(expected), 1))

    # 6. Retention rates within 10% tolerance (+0.3)
    expected_rates = {str(r[0]): float(r[3]) for r in expected}
    rate_correct = sum(
        1 for r in rows
        if len(r) >= 4 and str(r[0]) in expected_rates
        and abs(float(r[3] or 0) - expected_rates[str(r[0])]) < 0.1
    )
    score += 0.3 * (rate_correct / max(len(expected), 1))

    exact = set(map(tuple, rows)) == set(map(tuple, expected))

    return SQLReward(
        total=round(min(score, 1.0), 4),
        syntax_valid=True,
        columns_correct=cols_ok,
        row_count_score=round(rc_score, 4),
        exact_match=exact,
        error_message=None,
    )


# ---------------------------------------------------------------------------
# Task registry
# ---------------------------------------------------------------------------

ALL_TASKS = {
    "task_easy":   (TASK_EASY,   grade_easy),
    "task_medium": (TASK_MEDIUM, grade_medium),
    "task_hard":   (TASK_HARD,   grade_hard),
}