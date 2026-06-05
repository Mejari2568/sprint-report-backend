from collections import defaultdict
from config import DONE_STATUSES, INPROG_STATUSES, BUG_TYPES, CYCLE_BUCKETS, MAX_CYCLE_DAYS
from modules.date_utils import parse_date, days_between


# ── Status helpers ────────────────────────────────────────────────────────────
def is_done(status):
    return (status or '').lower().strip() in DONE_STATUSES

def is_inprog(status):
    return any(x in (status or '').lower().strip() for x in INPROG_STATUSES)

def is_bug(issue_type):
    return (issue_type or '').lower().strip() in BUG_TYPES


# ── Points helper ─────────────────────────────────────────────────────────────
def sum_points(tickets):
    return sum(float(t.get('points') or 0) for t in tickets)


# ── Cycle time ────────────────────────────────────────────────────────────────
def calc_cycle_times(tickets):
    cycle_times  = []
    missing_dates = []

    for t in tickets:
        dev_start = parse_date(t.get('dev_start'))
        uat_date  = parse_date(t.get('uat_date'))
        key       = t.get('key', '')
        summary   = (t.get('summary') or '')[:50]

        if dev_start and uat_date:
            ct = days_between(dev_start, uat_date)
            if ct is not None and 0 <= ct <= MAX_CYCLE_DAYS:
                cycle_times.append({
                    'days':     ct,
                    'key':      key,
                    'summary':  summary,
                    'points':   t.get('points', 0),
                    'assignee': t.get('assignee', ''),
                })
        else:
            missing_dates.append({
                'key':     key,
                'summary': summary,
                'missing': 'Dev Start' if not dev_start else 'UAT Date',
            })

    return cycle_times, missing_dates


def calc_cycle_stats(cycle_times):
    cycle_days = [c['days'] for c in cycle_times]
    if not cycle_days:
        return None, None, None, None, None

    ct_sorted = sorted(cycle_days)
    avg    = round(sum(ct_sorted) / len(ct_sorted), 1)
    p50    = ct_sorted[len(ct_sorted) // 2]
    p90    = ct_sorted[int(len(ct_sorted) * 0.9)] if len(ct_sorted) >= 5 else ct_sorted[-1]
    min_ct = min(ct_sorted)
    max_ct = max(ct_sorted)
    return avg, p50, p90, min_ct, max_ct


def bucket_cycle_times(cycle_times):
    cycle_days = [c['days'] for c in cycle_times]
    return [
        (label, sum(1 for t in cycle_days if lo <= t < hi))
        for lo, hi, label in CYCLE_BUCKETS
    ]


# ── Assignee breakdown ────────────────────────────────────────────────────────
def calc_assignee_map(tickets):
    assignee_map = defaultdict(lambda: {'done': 0, 'inprog': 0, 'todo': 0, 'pts': 0, 'total': 0})
    for t in tickets:
        a = (t.get('assignee') or 'Unassigned').strip()
        assignee_map[a]['total'] += 1
        assignee_map[a]['pts']   += float(t.get('points') or 0)
        if is_done(t.get('status')):
            assignee_map[a]['done']   += 1
        elif is_inprog(t.get('status')):
            assignee_map[a]['inprog'] += 1
        else:
            assignee_map[a]['todo']   += 1
    return dict(assignee_map)


# ── Epic breakdown ────────────────────────────────────────────────────────────
def calc_epic_map(tickets):
    epic_map = defaultdict(lambda: {'done': 0, 'total': 0, 'pts_done': 0, 'pts_total': 0})
    for t in tickets:
        ep = (t.get('epic') or t.get('labels') or 'No Epic / Label').strip()
        epic_map[ep]['total']     += 1
        epic_map[ep]['pts_total'] += float(t.get('points') or 0)
        if is_done(t.get('status')):
            epic_map[ep]['done']     += 1
            epic_map[ep]['pts_done'] += float(t.get('points') or 0)
    return dict(epic_map)


# ── Main analyse function ─────────────────────────────────────────────────────
def analyse(tickets, meta):
    total   = len(tickets)
    done    = [t for t in tickets if is_done(t.get('status'))]
    inprog  = [t for t in tickets if is_inprog(t.get('status'))]
    todo    = [t for t in tickets if not is_done(t.get('status')) and not is_inprog(t.get('status'))]
    bugs    = [t for t in tickets if is_bug(t.get('type'))]
    bugs_done = [t for t in bugs if is_done(t.get('status'))]
    stories = [t for t in tickets if not is_bug(t.get('type'))]

    total_pts  = sum_points(tickets)
    done_pts   = sum_points(done)
    inprog_pts = sum_points(inprog)
    todo_pts   = sum_points(todo)
    completion = round(done_pts / total_pts * 100) if total_pts else 0

    cycle_times, missing_dates = calc_cycle_times(tickets)
    cycle_days   = [c['days'] for c in cycle_times]
    avg_cycle, p50, p90, min_ct, max_ct = calc_cycle_stats(cycle_times)
    cycle_buckets = bucket_cycle_times(cycle_times)

    return {
        'meta':        meta,
        'total':       total,
        'done':        len(done),
        'inprog':      len(inprog),
        'todo':        len(todo),
        'total_pts':   round(total_pts),
        'done_pts':    round(done_pts),
        'inprog_pts':  round(inprog_pts),
        'todo_pts':    round(todo_pts),
        'completion':  completion,
        'bugs_total':  len(bugs),
        'bugs_done':   len(bugs_done),
        'bugs_open':   len(bugs) - len(bugs_done),
        'stories':     stories,
        'cycle_times':    cycle_times,
        'avg_cycle':      avg_cycle,
        'p50':            p50,
        'p90':            p90,
        'min_ct':         min_ct,
        'max_ct':         max_ct,
        'cycle_buckets':  cycle_buckets,
        'missing_dates':  missing_dates,
        'assignees':      calc_assignee_map(tickets),
        'epics':          calc_epic_map(tickets),
        'incomplete':     [t for t in tickets if not is_done(t.get('status'))],
        # QA bugs — populated later in app.py after analyse_bugs()
        'qa_bugs':        [],
        'story_bug_map':  {},
    }
