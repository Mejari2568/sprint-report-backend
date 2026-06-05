# ── Status Classification ─────────────────────────────────────────────────────
DONE_STATUSES = {
    'done', 'closed', 'resolved', 'released',
    'ready for prod', 'ready for release',
    'deployed', 'uat', 'ready for production'
}

INPROG_STATUSES = {
    'in progress', 'in development', 'in review',
    'in testing', 'testing', 'development',
    'review', 'in qa', 'qa'
}

BUG_TYPES = {'bug', 'defect'}

# ── Cycle Time Buckets ────────────────────────────────────────────────────────
CYCLE_BUCKETS = [
    (0,   5,   '0–5 days'),
    (5,   10,  '5–10 days'),
    (10,  15,  '10–15 days'),
    (15,  20,  '15–20 days'),
    (20,  30,  '20–30 days'),
    (30,  99999, '30+ days'),
]

# ── Epic Chart Colors ─────────────────────────────────────────────────────────
EPIC_COLORS = [
    '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b',
    '#10b981', '#06b6d4', '#f97316', '#6366f1'
]

# ── Max Cycle Time (days) — anything above this is treated as outlier ─────────
MAX_CYCLE_DAYS = 120
