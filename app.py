import os
from datetime import datetime, timezone
from collections import defaultdict
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ── Status classification ─────────────────────────────────────────────────────
DONE_STATUSES = {
    'done', 'closed', 'resolved', 'released',
    'ready for prod', 'ready for release', 'deployed'
}
INPROG_STATUSES = {
    'in progress', 'in development', 'in review', 'in testing',
    'uat', 'testing', 'development', 'review', 'in qa', 'qa'
}
BUG_TYPES = {'bug', 'defect'}


def is_done(status):
    return (status or '').lower().strip() in DONE_STATUSES


def is_inprog(status):
    s = (status or '').lower().strip()
    return any(x in s for x in INPROG_STATUSES)


def is_bug(issue_type):
    return (issue_type or '').lower().strip() in BUG_TYPES


# ── Date parsing ──────────────────────────────────────────────────────────────
def parse_date(val):
    if not val:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=None) if val.tzinfo else val
    formats = [
        '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S.%fZ',
        '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S',
        '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d',
        '%d-%b-%Y', '%b %d, %Y'
    ]
    for fmt in formats:
        try:
            return datetime.strptime(str(val).strip()[:19], fmt[:len(str(val).strip())])
        except Exception:
            continue
    return None


def days_between(d1, d2):
    if d1 and d2:
        delta = abs((d2 - d1).total_seconds()) / 86400
        return round(delta, 1)
    return None


# ── Core analytics ────────────────────────────────────────────────────────────
def analyse(tickets, meta):
    total     = len(tickets)
    done      = [t for t in tickets if is_done(t.get('status'))]
    inprog    = [t for t in tickets if is_inprog(t.get('status'))]
    todo      = [t for t in tickets if not is_done(t.get('status')) and not is_inprog(t.get('status'))]
    bugs      = [t for t in tickets if is_bug(t.get('type'))]
    bugs_done = [t for t in bugs if is_done(t.get('status'))]

    # Story points
    def pts(lst): return sum(float(t.get('points') or 0) for t in lst)
    total_pts    = pts(tickets)
    done_pts     = pts(done)
    inprog_pts   = pts(inprog)
    todo_pts     = pts(todo)
    completion   = round(done_pts / total_pts * 100) if total_pts else 0

    # Lead time & cycle time
    lead_times, cycle_times = [], []
    for t in done:
        created  = parse_date(t.get('created'))
        resolved = parse_date(t.get('resolved'))
        updated  = parse_date(t.get('updated'))
        if created and resolved:
            lt = days_between(created, resolved)
            if lt is not None:
                lead_times.append(lt)
        elif created and updated:
            lt = days_between(created, updated)
            if lt is not None:
                lead_times.append(lt)
        if resolved and updated:
            ct = days_between(updated, resolved)
            if ct and ct < 30:
                cycle_times.append(ct)

    avg_lead  = round(sum(lead_times)  / len(lead_times),  1) if lead_times  else None
    avg_cycle = round(sum(cycle_times) / len(cycle_times), 1) if cycle_times else None

    # Assignee breakdown
    assignee_map = defaultdict(lambda: {'done': 0, 'inprog': 0, 'todo': 0, 'pts': 0, 'total': 0})
    for t in tickets:
        a = (t.get('assignee') or 'Unassigned').strip()
        assignee_map[a]['total'] += 1
        assignee_map[a]['pts']   += float(t.get('points') or 0)
        if is_done(t.get('status')):   assignee_map[a]['done']   += 1
        elif is_inprog(t.get('status')): assignee_map[a]['inprog'] += 1
        else:                            assignee_map[a]['todo']   += 1

    # Priority breakdown
    priority_map = defaultdict(lambda: {'done': 0, 'total': 0})
    for t in tickets:
        p = (t.get('priority') or 'None').strip()
        priority_map[p]['total'] += 1
        if is_done(t.get('status')):
            priority_map[p]['done'] += 1

    # Epic / Label grouping
    epic_map = defaultdict(lambda: {'done': 0, 'total': 0, 'pts_done': 0, 'pts_total': 0})
    for t in tickets:
        ep = (t.get('epic') or t.get('labels') or 'No Epic / Label').strip()
        epic_map[ep]['total']     += 1
        epic_map[ep]['pts_total'] += float(t.get('points') or 0)
        if is_done(t.get('status')):
            epic_map[ep]['done']     += 1
            epic_map[ep]['pts_done'] += float(t.get('points') or 0)

    # Incomplete items
    incomplete = [t for t in tickets if not is_done(t.get('status'))]

    return {
        'meta':         meta,
        'total':        total,
        'done':         len(done),
        'inprog':       len(inprog),
        'todo':         len(todo),
        'total_pts':    round(total_pts),
        'done_pts':     round(done_pts),
        'inprog_pts':   round(inprog_pts),
        'todo_pts':     round(todo_pts),
        'completion':   completion,
        'bugs_total':   len(bugs),
        'bugs_done':    len(bugs_done),
        'bugs_open':    len(bugs) - len(bugs_done),
        'avg_lead':     avg_lead,
        'avg_cycle':    avg_cycle,
        'lead_times':   lead_times,
        'assignees':    dict(assignee_map),
        'priorities':   dict(priority_map),
        'epics':        dict(epic_map),
        'incomplete':   incomplete,
    }


# ── HTML report builder ───────────────────────────────────────────────────────
def build_html(d):
    meta = d['meta']
    sprint  = meta.get('sprint', 'Sprint')
    team    = meta.get('team', '')
    sm      = meta.get('scrum_master', '')
    dates   = meta.get('dates', '')
    goal    = meta.get('goal', '')
    notes   = meta.get('notes', '')
    now     = datetime.now().strftime('%d %b %Y, %H:%M')

    # helper
    def pct_bar(pct, color='#3dffa0'):
        return f'''<div style="background:rgba(255,255,255,0.07);border-radius:4px;height:6px;margin-top:6px">
          <div style="width:{min(pct,100)}%;background:{color};height:6px;border-radius:4px"></div></div>'''

    def badge(text, cls):
        colors = {
            'done':  ('rgba(61,255,160,0.12)', '#3dffa0', 'rgba(61,255,160,0.2)'),
            'prog':  ('rgba(91,138,240,0.12)', '#5b8af0', 'rgba(91,138,240,0.2)'),
            'todo':  ('rgba(255,255,255,0.05)', '#7a7f8e', 'rgba(255,255,255,0.13)'),
            'bug':   ('rgba(255,107,107,0.12)', '#ff6b6b', 'rgba(255,107,107,0.2)'),
            'warn':  ('rgba(255,179,71,0.12)',  '#ffb347', 'rgba(255,179,71,0.2)'),
        }
        bg, fg, border = colors.get(cls, colors['todo'])
        return f'<span style="display:inline-block;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:500;font-family:monospace;background:{bg};color:{fg};border:1px solid {border}">{text}</span>'

    # ── 1. Header ─────────────────────────────────────────────────────────────
    html = f'''
<h1 style="font-family:Georgia,serif;font-size:2rem;font-weight:300;color:#fff;margin-bottom:0.5rem">
  Sprint Report — <em style="font-style:italic;color:#3dffa0">{sprint}</em>
</h1>
<div style="display:flex;gap:2rem;flex-wrap:wrap;margin-bottom:1.5rem">
  {f'<div><span style="font-size:11px;color:#7a7f8e;display:block;font-family:monospace">TEAM</span><span style="color:#e8eaf0;font-weight:500">{team}</span></div>' if team else ''}
  {f'<div><span style="font-size:11px;color:#7a7f8e;display:block;font-family:monospace">SCRUM MASTER</span><span style="color:#e8eaf0;font-weight:500">{sm}</span></div>' if sm else ''}
  {f'<div><span style="font-size:11px;color:#7a7f8e;display:block;font-family:monospace">DATES</span><span style="color:#e8eaf0;font-weight:500">{dates}</span></div>' if dates else ''}
  <div><span style="font-size:11px;color:#7a7f8e;display:block;font-family:monospace">GENERATED</span><span style="color:#e8eaf0;font-weight:500">{now}</span></div>
</div>
{f'<div style="background:rgba(91,138,240,0.07);border:1px solid rgba(91,138,240,0.18);border-radius:10px;padding:0.9rem 1.2rem;margin-bottom:1.5rem;font-size:14px;color:#e8eaf0"><strong style="color:#5b8af0">Sprint Goal:</strong> {goal}</div>' if goal else ''}
<div style="height:1px;background:rgba(255,255,255,0.07);margin:1.5rem 0"></div>
'''

    # ── 2. Sprint Summary ─────────────────────────────────────────────────────
    html += f'''
<h2 style="font-family:monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#5b8af0;margin:2rem 0 1rem">01 · Sprint Summary</h2>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:10px;margin-bottom:1.5rem">
  <div style="background:#1e2128;border-radius:10px;padding:14px;text-align:center;border:1px solid rgba(255,255,255,0.07)">
    <div style="font-family:monospace;font-size:26px;color:#fff">{d['total']}</div>
    <div style="font-size:11px;color:#7a7f8e;text-transform:uppercase;margin-top:4px">Total Tickets</div>
  </div>
  <div style="background:#1e2128;border-radius:10px;padding:14px;text-align:center;border:1px solid rgba(255,255,255,0.07)">
    <div style="font-family:monospace;font-size:26px;color:#3dffa0">{d['done']}</div>
    <div style="font-size:11px;color:#7a7f8e;text-transform:uppercase;margin-top:4px">Completed</div>
  </div>
  <div style="background:#1e2128;border-radius:10px;padding:14px;text-align:center;border:1px solid rgba(255,255,255,0.07)">
    <div style="font-family:monospace;font-size:26px;color:#5b8af0">{d['inprog']}</div>
    <div style="font-size:11px;color:#7a7f8e;text-transform:uppercase;margin-top:4px">In Progress</div>
  </div>
  <div style="background:#1e2128;border-radius:10px;padding:14px;text-align:center;border:1px solid rgba(255,255,255,0.07)">
    <div style="font-family:monospace;font-size:26px;color:#7a7f8e">{d['todo']}</div>
    <div style="font-size:11px;color:#7a7f8e;text-transform:uppercase;margin-top:4px">To Do</div>
  </div>
  <div style="background:#1e2128;border-radius:10px;padding:14px;text-align:center;border:1px solid rgba(255,255,255,0.07)">
    <div style="font-family:monospace;font-size:26px;color:#fff">{d['completion']}%</div>
    <div style="font-size:11px;color:#7a7f8e;text-transform:uppercase;margin-top:4px">Completion</div>
  </div>
</div>

<div style="background:#1e2128;border-radius:10px;padding:1.2rem;border:1px solid rgba(255,255,255,0.07);margin-bottom:1rem">
  <div style="display:flex;justify-content:space-between;margin-bottom:6px">
    <span style="font-size:13px;color:#e8eaf0;font-weight:500">Story Points Progress</span>
    <span style="font-family:monospace;font-size:13px;color:#3dffa0">{d['done_pts']} / {d['total_pts']} pts</span>
  </div>
  {pct_bar(d['completion'])}
  <div style="display:flex;gap:1.5rem;margin-top:10px;font-size:12px;color:#7a7f8e">
    <span>✅ Done: <strong style="color:#3dffa0">{d['done_pts']} pts</strong></span>
    <span>🔵 In Progress: <strong style="color:#5b8af0">{d['inprog_pts']} pts</strong></span>
    <span>⚪ To Do: <strong style="color:#7a7f8e">{d['todo_pts']} pts</strong></span>
  </div>
</div>
{f'<div style="background:rgba(255,179,71,0.07);border:1px solid rgba(255,179,71,0.2);border-radius:10px;padding:0.9rem 1.2rem;margin-bottom:1rem;font-size:14px;color:#e8eaf0">⚠️ <strong>Additional Notes:</strong> {notes}</div>' if notes else ''}
<div style="height:1px;background:rgba(255,255,255,0.07);margin:1.5rem 0"></div>
'''

    # ── 3. Ticket Status Breakdown ────────────────────────────────────────────
    html += '''<h2 style="font-family:monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#5b8af0;margin:2rem 0 1rem">02 · Ticket Status Breakdown</h2>'''

    # Status distribution visual bars
    for label, count, color, cls in [
        ('Done',        d['done'],   '#3dffa0', 'done'),
        ('In Progress', d['inprog'], '#5b8af0', 'prog'),
        ('To Do',       d['todo'],   '#7a7f8e', 'todo'),
    ]:
        pct = round(count / d['total'] * 100) if d['total'] else 0
        html += f'''
<div style="margin-bottom:10px">
  <div style="display:flex;justify-content:space-between;margin-bottom:4px">
    <span style="font-size:13px;color:#e8eaf0">{badge(label, cls)} &nbsp; {count} tickets</span>
    <span style="font-family:monospace;font-size:12px;color:{color}">{pct}%</span>
  </div>
  {pct_bar(pct, color)}
</div>'''

    html += '<div style="height:1px;background:rgba(255,255,255,0.07);margin:1.5rem 0"></div>'

    # ── 4. Lead Time & Cycle Time ─────────────────────────────────────────────
    html += '<h2 style="font-family:monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#5b8af0;margin:2rem 0 1rem">03 · Lead Time &amp; Cycle Time</h2>'

    if d['avg_lead'] or d['avg_cycle']:
        html += f'''
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:1rem">
  <div style="background:#1e2128;border-radius:10px;padding:1.2rem;border:1px solid rgba(255,255,255,0.07);text-align:center">
    <div style="font-family:monospace;font-size:2.5rem;color:#fff">{d['avg_lead'] if d['avg_lead'] else '—'}</div>
    <div style="font-size:12px;color:#7a7f8e;margin-top:4px;text-transform:uppercase">Avg Lead Time (days)</div>
    <div style="font-size:11px;color:#5b8af0;margin-top:6px">Created → Resolved</div>
  </div>
  <div style="background:#1e2128;border-radius:10px;padding:1.2rem;border:1px solid rgba(255,255,255,0.07);text-align:center">
    <div style="font-family:monospace;font-size:2.5rem;color:#fff">{d['avg_cycle'] if d['avg_cycle'] else '—'}</div>
    <div style="font-size:12px;color:#7a7f8e;margin-top:4px;text-transform:uppercase">Avg Cycle Time (days)</div>
    <div style="font-size:11px;color:#5b8af0;margin-top:6px">In Progress → Done</div>
  </div>
</div>'''

        if d['lead_times']:
            lt_sorted = sorted(d['lead_times'])
            p50 = lt_sorted[len(lt_sorted)//2]
            p90 = lt_sorted[int(len(lt_sorted)*0.9)] if len(lt_sorted) >= 5 else lt_sorted[-1]
            html += f'''
<div style="background:#1e2128;border-radius:10px;padding:1rem 1.2rem;border:1px solid rgba(255,255,255,0.07);margin-bottom:1rem">
  <div style="display:flex;gap:2rem;flex-wrap:wrap;font-size:13px">
    <span style="color:#7a7f8e">Min: <strong style="color:#e8eaf0">{min(lt_sorted)}d</strong></span>
    <span style="color:#7a7f8e">Median (P50): <strong style="color:#e8eaf0">{p50}d</strong></span>
    <span style="color:#7a7f8e">P90: <strong style="color:#e8eaf0">{p90}d</strong></span>
    <span style="color:#7a7f8e">Max: <strong style="color:#e8eaf0">{max(lt_sorted)}d</strong></span>
    <span style="color:#7a7f8e">Samples: <strong style="color:#e8eaf0">{len(lt_sorted)}</strong></span>
  </div>
</div>'''
    else:
        html += '<div style="background:rgba(255,179,71,0.07);border:1px solid rgba(255,179,71,0.2);border-radius:10px;padding:0.9rem 1.2rem;font-size:14px;color:#e8eaf0">⚠️ Lead/Cycle time requires <strong>Created</strong> and <strong>Resolved</strong> date columns in your Excel export. Add these columns from Jira to unlock this section.</div>'

    html += '<div style="height:1px;background:rgba(255,255,255,0.07);margin:1.5rem 0"></div>'

    # ── 5. Bug / Defect Analysis ──────────────────────────────────────────────
    html += '<h2 style="font-family:monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#5b8af0;margin:2rem 0 1rem">04 · Bug / Defect Analysis</h2>'

    if d['bugs_total'] > 0:
        bug_fix_rate = round(d['bugs_done'] / d['bugs_total'] * 100)
        bug_density  = round(d['bugs_total'] / d['total_pts'], 2) if d['total_pts'] else 'N/A'
        html += f'''
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:1rem">
  <div style="background:#1e2128;border-radius:10px;padding:14px;text-align:center;border:1px solid rgba(255,107,107,0.2)">
    <div style="font-family:monospace;font-size:26px;color:#ff6b6b">{d['bugs_total']}</div>
    <div style="font-size:11px;color:#7a7f8e;text-transform:uppercase;margin-top:4px">Total Bugs</div>
  </div>
  <div style="background:#1e2128;border-radius:10px;padding:14px;text-align:center;border:1px solid rgba(61,255,160,0.2)">
    <div style="font-family:monospace;font-size:26px;color:#3dffa0">{d['bugs_done']}</div>
    <div style="font-size:11px;color:#7a7f8e;text-transform:uppercase;margin-top:4px">Fixed</div>
  </div>
  <div style="background:#1e2128;border-radius:10px;padding:14px;text-align:center;border:1px solid rgba(255,179,71,0.2)">
    <div style="font-family:monospace;font-size:26px;color:#ffb347">{d['bugs_open']}</div>
    <div style="font-size:11px;color:#7a7f8e;text-transform:uppercase;margin-top:4px">Open</div>
  </div>
  <div style="background:#1e2128;border-radius:10px;padding:14px;text-align:center;border:1px solid rgba(255,255,255,0.07)">
    <div style="font-family:monospace;font-size:26px;color:#fff">{bug_fix_rate}%</div>
    <div style="font-size:11px;color:#7a7f8e;text-transform:uppercase;margin-top:4px">Fix Rate</div>
  </div>
  <div style="background:#1e2128;border-radius:10px;padding:14px;text-align:center;border:1px solid rgba(255,255,255,0.07)">
    <div style="font-family:monospace;font-size:26px;color:#fff">{bug_density}</div>
    <div style="font-size:11px;color:#7a7f8e;text-transform:uppercase;margin-top:4px">Bugs/SP</div>
  </div>
</div>
<div style="margin-bottom:10px">
  <div style="display:flex;justify-content:space-between;margin-bottom:4px">
    <span style="font-size:13px;color:#e8eaf0">Bug Fix Progress</span>
    <span style="font-family:monospace;font-size:12px;color:#3dffa0">{bug_fix_rate}%</span>
  </div>
  {pct_bar(bug_fix_rate, '#3dffa0')}
</div>'''
        if bug_density != 'N/A' and isinstance(bug_density, float):
            if bug_density < 0.1:
                health = ('🟢 Excellent', '#3dffa0')
            elif bug_density < 0.3:
                health = ('🟡 Acceptable', '#ffb347')
            else:
                health = ('🔴 Needs Attention', '#ff6b6b')
            html += f'<p style="font-size:13px;color:#7a7f8e;margin-top:8px">Bug Density Health: <strong style="color:{health[1]}">{health[0]}</strong> ({bug_density} bugs per story point)</p>'
    else:
        html += '<div style="background:rgba(61,255,160,0.07);border:1px solid rgba(61,255,160,0.2);border-radius:10px;padding:0.9rem 1.2rem;font-size:14px;color:#e8eaf0">🟢 No bugs or defects found in this sprint. Great quality!</div>'

    html += '<div style="height:1px;background:rgba(255,255,255,0.07);margin:1.5rem 0"></div>'

    # ── 6. Epic / Label Progress ──────────────────────────────────────────────
    html += '<h2 style="font-family:monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#5b8af0;margin:2rem 0 1rem">05 · Epic / Label Progress</h2>'

    if d['epics']:
        html += '<table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:1rem">'
        html += '<thead><tr>'
        for col in ['Epic / Label', 'Done', 'Total', 'Pts Done', 'Pts Total', 'Progress']:
            html += f'<th style="text-align:left;padding:7px 10px;color:#7a7f8e;border-bottom:1px solid rgba(255,255,255,0.07);font-family:monospace;font-size:11px">{col}</th>'
        html += '</tr></thead><tbody>'
        for ep, v in sorted(d['epics'].items(), key=lambda x: -x[1]['pts_total']):
            ep_pct = round(v['done'] / v['total'] * 100) if v['total'] else 0
            ep_color = '#3dffa0' if ep_pct == 100 else '#5b8af0' if ep_pct >= 50 else '#ffb347'
            html += f'''<tr>
              <td style="padding:8px 10px;border-bottom:1px solid rgba(255,255,255,0.07);color:#e8eaf0;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{ep}</td>
              <td style="padding:8px 10px;border-bottom:1px solid rgba(255,255,255,0.07);color:#3dffa0;font-family:monospace">{v['done']}</td>
              <td style="padding:8px 10px;border-bottom:1px solid rgba(255,255,255,0.07);color:#e8eaf0;font-family:monospace">{v['total']}</td>
              <td style="padding:8px 10px;border-bottom:1px solid rgba(255,255,255,0.07);color:#3dffa0;font-family:monospace">{round(v['pts_done'])}</td>
              <td style="padding:8px 10px;border-bottom:1px solid rgba(255,255,255,0.07);color:#e8eaf0;font-family:monospace">{round(v['pts_total'])}</td>
              <td style="padding:8px 10px;border-bottom:1px solid rgba(255,255,255,0.07);min-width:120px">
                <div style="display:flex;align-items:center;gap:8px">
                  <div style="flex:1;background:rgba(255,255,255,0.07);border-radius:4px;height:5px">
                    <div style="width:{ep_pct}%;background:{ep_color};height:5px;border-radius:4px"></div>
                  </div>
                  <span style="font-family:monospace;font-size:11px;color:{ep_color}">{ep_pct}%</span>
                </div>
              </td>
            </tr>'''
        html += '</tbody></table>'
    else:
        html += '<p style="color:#7a7f8e;font-size:14px">No Epic or Label data found. Add <strong>Epic Name</strong> or <strong>Labels</strong> column to your Jira export.</p>'

    html += '<div style="height:1px;background:rgba(255,255,255,0.07);margin:1.5rem 0"></div>'

    # ── 7. Incomplete Items ───────────────────────────────────────────────────
    html += f'<h2 style="font-family:monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#5b8af0;margin:2rem 0 1rem">06 · Incomplete Items ({len(d["incomplete"])})</h2>'

    if d['incomplete']:
        html += '<table style="width:100%;border-collapse:collapse;font-size:13px">'
        html += '<thead><tr>'
        for col in ['Key', 'Summary', 'Type', 'Status', 'Points', 'Assignee']:
            html += f'<th style="text-align:left;padding:7px 10px;color:#7a7f8e;border-bottom:1px solid rgba(255,255,255,0.07);font-family:monospace;font-size:11px">{col}</th>'
        html += '</tr></thead><tbody>'

        for t in d['incomplete']:
            status = t.get('status') or 'To Do'
            status_color = '#5b8af0' if is_inprog(status) else '#7a7f8e'
            type_color   = '#ff6b6b' if is_bug(t.get('type')) else '#7a7f8e'
            html += f'''<tr style="border-bottom:1px solid rgba(255,255,255,0.05)">
              <td style="padding:7px 10px;color:#5b8af0;font-family:monospace;font-size:12px">{t.get('key','—')}</td>
              <td style="padding:7px 10px;color:#e8eaf0;max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{t.get('summary','')}">{(t.get('summary') or '—')[:50]}</td>
              <td style="padding:7px 10px;color:{type_color};font-size:12px">{t.get('type','—')}</td>
              <td style="padding:7px 10px;color:{status_color};font-size:12px">{status}</td>
              <td style="padding:7px 10px;color:#e8eaf0;font-family:monospace;text-align:center">{t.get('points','—')}</td>
              <td style="padding:7px 10px;color:#7a7f8e;font-size:12px">{t.get('assignee','Unassigned')}</td>
            </tr>'''
        html += '</tbody></table>'

        open_pts = sum(float(t.get('points') or 0) for t in d['incomplete'])
        html += f'<p style="font-size:12px;color:#7a7f8e;margin-top:10px">Total carry-over: <strong style="color:#ffb347">{round(open_pts)} story points</strong> across {len(d["incomplete"])} tickets</p>'
    else:
        html += '<div style="background:rgba(61,255,160,0.07);border:1px solid rgba(61,255,160,0.2);border-radius:10px;padding:0.9rem 1.2rem;font-size:14px;color:#e8eaf0">🎉 All tickets completed! Perfect sprint delivery.</div>'

    # ── Footer ────────────────────────────────────────────────────────────────
    html += f'''
<div style="height:1px;background:rgba(255,255,255,0.07);margin:2rem 0 1rem"></div>
<p style="font-size:11px;color:#7a7f8e;font-family:monospace;text-align:center">
  Generated on {now} · {sprint} · {team}
</p>'''

    return html


# ── API endpoint ──────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Sprint Report API is running"})


@app.route("/generate-report", methods=["POST"])
def generate_report():
    try:
        body    = request.get_json()
        meta    = {
            "sprint":        body.get("sprint", "Sprint"),
            "dates":         body.get("dates", ""),
            "team":          body.get("team", ""),
            "scrum_master":  body.get("scrum_master", ""),
            "goal":          body.get("goal", ""),
            "notes":         body.get("notes", ""),
        }
        tickets = body.get("tickets", [])
        data    = analyse(tickets, meta)
        html    = build_html(data)
        return jsonify({"success": True, "html": html})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
