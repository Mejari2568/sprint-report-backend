import os
import json
from datetime import datetime
from collections import defaultdict
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ── Status classification ─────────────────────────────────────────────────────
DONE_STATUSES   = {'done','closed','resolved','released','ready for prod','ready for release','deployed','uat','ready for production'}
INPROG_STATUSES = {'in progress','in development','in review','in testing','testing','development','review','in qa','qa'}
BUG_TYPES       = {'bug','defect'}

def is_done(s):   return (s or '').lower().strip() in DONE_STATUSES
def is_inprog(s): return any(x in (s or '').lower().strip() for x in INPROG_STATUSES)
def is_bug(t):    return (t or '').lower().strip() in BUG_TYPES

def parse_date(val):
    if not val or str(val).strip() in ('', 'nan', 'None', '[no field found]'): return None
    if isinstance(val, datetime): return val.replace(tzinfo=None) if val.tzinfo else val
    # Handle Excel serial numbers passed as strings e.g. "46000.0"
    try:
        serial = float(str(val).strip())
        if 30000 < serial < 60000:
            from datetime import timedelta
            return datetime(1899, 12, 30) + timedelta(days=serial)
    except: pass
    # Try common date string formats
    s = str(val).strip()
    # Try full string first, then truncated
    for fmt in ['%Y-%m-%d','%Y-%m-%d %H:%M:%S','%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f','%d/%m/%Y','%m/%d/%Y',
                '%d-%m-%Y','%d-%b-%Y','%b %d, %Y','%m/%d/%Y %H:%M',
                '%m/%d/%Y %H:%M:%S','%Y/%m/%d','%m/%d/%y','%d/%m/%y']:
        try: return datetime.strptime(s, fmt)
        except: pass
        try: return datetime.strptime(s[:10], fmt[:10])
        except: pass
    print(f"parse_date FAILED for: {repr(val)}")
    return None

def days_between(d1, d2):
    if d1 and d2:
        delta = abs((d2 - d1).total_seconds()) / 86400
        return round(delta, 1)
    return None


# ── Analytics ─────────────────────────────────────────────────────────────────
def analyse(tickets, meta):
    total     = len(tickets)
    done      = [t for t in tickets if is_done(t.get('status'))]
    inprog    = [t for t in tickets if is_inprog(t.get('status'))]
    todo      = [t for t in tickets if not is_done(t.get('status')) and not is_inprog(t.get('status'))]
    bugs      = [t for t in tickets if is_bug(t.get('type'))]
    bugs_done = [t for t in bugs   if is_done(t.get('status'))]

    def pts(lst): return sum(float(t.get('points') or 0) for t in lst)
    total_pts = pts(tickets); done_pts = pts(done)
    inprog_pts = pts(inprog); todo_pts = pts(todo)
    completion = round(done_pts / total_pts * 100) if total_pts else 0

    lead_times, cycle_times = [], []
    missing_dates = []
    for t in tickets:
        dev_start = parse_date(t.get('dev_start'))
        uat_date  = parse_date(t.get('uat_date'))
        key       = t.get('key','')
        summary   = (t.get('summary') or '')[:50]

        if dev_start and uat_date:
            ct = days_between(dev_start, uat_date)
            if ct is not None and 0 <= ct <= 120:
                cycle_times.append({
                    'days': ct,
                    'key': key,
                    'summary': summary,
                    'points': t.get('points', 0),
                    'assignee': t.get('assignee','')
                })
        else:
            # track which date is missing
            missing_dates.append({
                'key': key,
                'summary': summary,
                'missing': 'Dev Start' if not dev_start else 'UAT Date'
            })

    avg_lead  = None
    cycle_days = [c['days'] for c in cycle_times]
    avg_cycle = round(sum(cycle_days) / len(cycle_days), 1) if cycle_days else None

    # Cycle time bucketing only
    BUCKETS = [(0,5,'0–5 days'),(5,10,'5–10 days'),(10,15,'10–15 days'),(15,20,'15–20 days'),(20,30,'20–30 days'),(30,99999,'30+ days')]
    def bucket_data(times):
        return [(label, sum(1 for t in times if lo <= t < hi)) for lo, hi, label in BUCKETS]
    lead_buckets  = []
    cycle_buckets = bucket_data(cycle_days)

    assignee_map = defaultdict(lambda: {'done':0,'inprog':0,'todo':0,'pts':0,'total':0})
    for t in tickets:
        a = (t.get('assignee') or 'Unassigned').strip()
        assignee_map[a]['total'] += 1
        assignee_map[a]['pts']   += float(t.get('points') or 0)
        if is_done(t.get('status')):     assignee_map[a]['done']   += 1
        elif is_inprog(t.get('status')): assignee_map[a]['inprog'] += 1
        else:                            assignee_map[a]['todo']    += 1

    epic_map = defaultdict(lambda: {'done':0,'total':0,'pts_done':0,'pts_total':0})
    for t in tickets:
        ep = (t.get('epic') or t.get('labels') or 'No Epic / Label').strip()
        epic_map[ep]['total']     += 1
        epic_map[ep]['pts_total'] += float(t.get('points') or 0)
        if is_done(t.get('status')):
            epic_map[ep]['done']     += 1
            epic_map[ep]['pts_done'] += float(t.get('points') or 0)

    return {
        'meta': meta, 'total': total,
        'done': len(done), 'inprog': len(inprog), 'todo': len(todo),
        'total_pts': round(total_pts), 'done_pts': round(done_pts),
        'inprog_pts': round(inprog_pts), 'todo_pts': round(todo_pts),
        'completion': completion,
        'bugs_total': len(bugs), 'bugs_done': len(bugs_done),
        'bugs_open': len(bugs) - len(bugs_done),
        'avg_lead': None, 'avg_cycle': avg_cycle, 'lead_times': [], 'cycle_times': cycle_times, 'missing_dates': missing_dates,
        'lead_buckets': [], 'cycle_buckets': cycle_buckets,
        'assignees': dict(assignee_map),
        'epics': dict(epic_map),
        'incomplete': [t for t in tickets if not is_done(t.get('status'))],
    }


# ── SVG chart helpers ─────────────────────────────────────────────────────────
def donut_chart(done, inprog, todo, size=140):
    total = done + inprog + todo or 1
    cx = cy = size / 2
    r = size / 2 - 14
    circumference = 2 * 3.14159 * r

    def arc(value, color, offset):
        pct = value / total
        dash = pct * circumference
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="18" stroke-dasharray="{dash:.1f} {circumference:.1f}" stroke-dashoffset="-{offset:.1f}" stroke-linecap="butt"/>'

    done_dash  = done  / total * circumference
    prog_dash  = inprog / total * circumference
    done_pct   = round(done / total * 100)

    svg = f'''<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" style="-webkit-print-color-adjust:exact;print-color-adjust:exact">
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#e8edf5" stroke-width="18"/>
      {arc(done,   "#10b981", 0)}
      {arc(inprog, "#3b82f6", done_dash)}
      {arc(todo,   "#e2e8f0", done_dash + prog_dash)}
      <text x="{cx}" y="{cy-6}" text-anchor="middle" font-size="20" font-weight="700" fill="#1e293b" font-family="Arial">{done_pct}%</text>
      <text x="{cx}" y="{cy+14}" text-anchor="middle" font-size="10" fill="#64748b" font-family="Arial">Done</text>
    </svg>'''
    return svg


def horizontal_bar_chart(items, max_val, colors):
    """items = list of (label, value) tuples"""
    bar_h = 28
    gap   = 10
    label_w = 130
    bar_area = 260
    total_h = len(items) * (bar_h + gap) + 10

    svg = f'<svg width="{label_w + bar_area + 60}" height="{total_h}" viewBox="0 0 {label_w + bar_area + 60} {total_h}" style="-webkit-print-color-adjust:exact;print-color-adjust:exact" font-family="Arial">'
    for i, (label, val, color) in enumerate(items):
        y = i * (bar_h + gap)
        bar_w = int((val / max_val) * bar_area) if max_val else 0
        svg += f'''
      <text x="0" y="{y + bar_h - 8}" font-size="12" fill="#374151" font-weight="500">{label[:18]}</text>
      <rect x="{label_w}" y="{y+4}" width="{bar_area}" height="{bar_h-8}" rx="4" fill="#f1f5f9" style="-webkit-print-color-adjust:exact;print-color-adjust:exact"/>
      <rect x="{label_w}" y="{y+4}" width="{bar_w}" height="{bar_h-8}" rx="4" fill="{color}" style="-webkit-print-color-adjust:exact;print-color-adjust:exact"/>
      <text x="{label_w + bar_w + 8}" y="{y + bar_h - 8}" font-size="12" fill="#374151" font-weight="600">{val}</text>'''
    svg += '</svg>'
    return svg


def pie_chart(segments, size=160):
    """segments = list of (label, value, color)"""
    total = sum(v for _, v, _ in segments) or 1
    cx = cy = size / 2
    r  = size / 2 - 10
    svg = f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" style="-webkit-print-color-adjust:exact;print-color-adjust:exact">'
    import math
    angle = -math.pi / 2
    for label, val, color in segments:
        if val == 0: continue
        sweep = 2 * math.pi * val / total
        x1 = cx + r * math.cos(angle)
        y1 = cy + r * math.sin(angle)
        x2 = cx + r * math.cos(angle + sweep)
        y2 = cy + r * math.sin(angle + sweep)
        large = 1 if sweep > math.pi else 0
        svg += f'<path d="M{cx},{cy} L{x1:.1f},{y1:.1f} A{r},{r} 0 {large},1 {x2:.1f},{y2:.1f} Z" fill="{color}" style="-webkit-print-color-adjust:exact;print-color-adjust:exact"/>'
        angle += sweep
    svg += '</svg>'
    return svg


# ── HTML / PDF report ─────────────────────────────────────────────────────────
def build_html(d):
    meta   = d['meta']
    sprint = meta.get('sprint','Sprint')
    team   = meta.get('team','')
    sm     = meta.get('scrum_master','')
    dates  = meta.get('dates','')
    goal   = meta.get('goal','')
    notes  = meta.get('notes','')
    now    = datetime.now().strftime('%d %b %Y, %H:%M')

    # print-safe progress bar using inline SVG rect
    def prog_bar(pct, color='#10b981', w=400, h=10):
        fill_w = int(pct / 100 * w)
        return f'''<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" style="max-width:100%;-webkit-print-color-adjust:exact;print-color-adjust:exact">
          <rect width="{w}" height="{h}" rx="5" fill="#e2e8f0"/>
          <rect width="{fill_w}" height="{h}" rx="5" fill="{color}" style="-webkit-print-color-adjust:exact;print-color-adjust:exact"/>
        </svg>'''

    # stat card
    def stat(val, label, color='#1e293b', bg='#f8fafc', border='#e2e8f0'):
        return f'''<div style="background:{bg};border:1.5px solid {border};border-radius:12px;padding:16px;text-align:center;-webkit-print-color-adjust:exact;print-color-adjust:exact">
          <div style="font-size:28px;font-weight:700;color:{color};font-family:Arial">{val}</div>
          <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.05em;margin-top:4px;font-family:Arial">{label}</div>
        </div>'''

    def section_title(num, title):
        return f'''<div style="display:flex;align-items:center;gap:12px;margin:2.5rem 0 1.2rem;page-break-inside:avoid">
          <div style="background:#1e40af;color:#fff;border-radius:8px;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;font-family:Arial;flex-shrink:0;-webkit-print-color-adjust:exact;print-color-adjust:exact">{num}</div>
          <h2 style="font-size:15px;font-weight:700;color:#1e293b;font-family:Arial;margin:0;text-transform:uppercase;letter-spacing:.06em">{title}</h2>
          <div style="flex:1;height:1.5px;background:linear-gradient(to right,#3b82f6,transparent);-webkit-print-color-adjust:exact;print-color-adjust:exact"></div>
        </div>'''

    donut = donut_chart(d['done'], d['inprog'], d['todo'])

    # ── PAGE STYLES ───────────────────────────────────────────────────────────
    html = '''<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #fff; }
@media print {
  * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
  .no-print { display: none !important; }
  .page-break { page-break-before: always; }
}
table { border-collapse: collapse; width: 100%; }
th, td { font-family: Arial, sans-serif; }
</style>'''

    # ── COVER HEADER ─────────────────────────────────────────────────────────
    html += f'''
<div style="background:linear-gradient(135deg,#1e3a8a 0%,#1d4ed8 60%,#0ea5e9 100%);border-radius:16px;padding:2.5rem 2rem;margin-bottom:2rem;-webkit-print-color-adjust:exact;print-color-adjust:exact">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:1rem">
    <div>
      <div style="font-size:11px;color:rgba(255,255,255,0.65);letter-spacing:.15em;text-transform:uppercase;font-family:Arial;margin-bottom:8px">Sprint Report</div>
      <h1 style="font-family:Arial;font-size:2rem;font-weight:800;color:#fff;margin-bottom:6px">{sprint}</h1>
      {f'<div style="font-size:14px;color:rgba(255,255,255,0.8);font-family:Arial">{team}</div>' if team else ''}
    </div>
    <div style="text-align:right">
      {f'<div style="font-size:13px;color:rgba(255,255,255,0.75);font-family:Arial">📅 {dates}</div>' if dates else ''}
      {f'<div style="font-size:13px;color:rgba(255,255,255,0.75);font-family:Arial;margin-top:4px">👤 {sm}</div>' if sm else ''}
      <div style="font-size:11px;color:rgba(255,255,255,0.5);font-family:Arial;margin-top:8px">Generated {now}</div>
    </div>
  </div>
  {f'<div style="margin-top:1.2rem;background:rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;font-size:13px;color:rgba(255,255,255,0.9);font-family:Arial;border-left:3px solid rgba(255,255,255,0.4)"><strong>Goal:</strong> {goal}</div>' if goal else ''}
</div>
'''

    # ── 1. SPRINT SUMMARY ────────────────────────────────────────────────────
    html += section_title('01', 'Sprint Summary')
    html += f'''<div style="display:flex;gap:1.5rem;align-items:center;flex-wrap:wrap;margin-bottom:1.5rem">
      <div style="flex-shrink:0">{donut}</div>
      <div style="flex:1;min-width:220px">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
          {stat(d['total'], 'Total Tickets', '#1e293b')}
          {stat(d['done'],  'Completed', '#059669', '#f0fdf4', '#bbf7d0')}
          {stat(d['inprog'],'In Progress', '#1d4ed8', '#eff6ff', '#bfdbfe')}
          {stat(d['todo'],  'To Do', '#64748b', '#f8fafc', '#e2e8f0')}
        </div>
      </div>
    </div>

    <div style="background:#f8fafc;border-radius:12px;padding:1.2rem;border:1px solid #e2e8f0;margin-bottom:1rem;-webkit-print-color-adjust:exact;print-color-adjust:exact">
      <div style="display:flex;justify-content:space-between;margin-bottom:8px">
        <span style="font-size:14px;font-weight:600;color:#1e293b;font-family:Arial">Story Points Progress</span>
        <span style="font-size:14px;font-weight:700;color:#059669;font-family:Arial">{d['done_pts']} / {d['total_pts']} pts ({d['completion']}%)</span>
      </div>
      {prog_bar(d['completion'])}
      <div style="display:flex;gap:1.5rem;margin-top:10px;font-size:12px;font-family:Arial;flex-wrap:wrap">
        <span style="color:#059669">✅ Done: <strong>{d['done_pts']} pts</strong></span>
        <span style="color:#1d4ed8">🔵 In Progress: <strong>{d['inprog_pts']} pts</strong></span>
        <span style="color:#64748b">⚪ To Do: <strong>{d['todo_pts']} pts</strong></span>
      </div>
    </div>
    {f'<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:10px 14px;font-size:13px;color:#92400e;font-family:Arial;-webkit-print-color-adjust:exact;print-color-adjust:exact">⚠️ <strong>Notes:</strong> {notes}</div>' if notes else ''}
'''

    # ── 2. STATUS BREAKDOWN ───────────────────────────────────────────────────
    html += section_title('02', 'Ticket Status Breakdown')
    status_items = [
        ('Done',        d['done'],   '#10b981'),
        ('In Progress', d['inprog'], '#3b82f6'),
        ('To Do',       d['todo'],   '#94a3b8'),
    ]
    max_s = max(d['done'], d['inprog'], d['todo'], 1)
    html += f'''<div style="display:flex;gap:2rem;align-items:center;flex-wrap:wrap;margin-bottom:1rem">
      <div>{horizontal_bar_chart([(l,v,c) for l,v,c in status_items], max_s, [])}</div>
      <div style="display:flex;flex-direction:column;gap:8px">'''
    for label, val, color in status_items:
        pct = round(val / d['total'] * 100) if d['total'] else 0
        html += f'<div style="display:flex;align-items:center;gap:8px;font-family:Arial;font-size:13px"><div style="width:12px;height:12px;border-radius:3px;background:{color};-webkit-print-color-adjust:exact;print-color-adjust:exact"></div><span style="color:#374151">{label}: <strong>{val}</strong> ({pct}%)</span></div>'
    html += '</div></div>'


    # ── 3. CYCLE TIME ────────────────────────────────────────────────────────
    html += section_title('03', 'Cycle Time Analysis')
    cycle_times = d.get('cycle_times', [])
    cycle_days  = [c['days'] for c in cycle_times]

    if cycle_days:
        ct_sorted = sorted(cycle_days)
        avg_ct = round(sum(ct_sorted) / len(ct_sorted), 1)
        p50    = ct_sorted[len(ct_sorted)//2]
        p90    = ct_sorted[int(len(ct_sorted)*0.9)] if len(ct_sorted) >= 5 else ct_sorted[-1]
        min_ct = min(ct_sorted)
        max_ct = max(ct_sorted)

        # KPI cards
        html += f'''<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:1.5rem">
          {stat(f"{avg_ct}d", "Avg Cycle Time", "#7c3aed", "#f5f3ff", "#ddd6fe")}
          {stat(f"{p50}d",    "Median (P50)",   "#0369a1", "#f0f9ff", "#bae6fd")}
          {stat(f"{p90}d",    "P90",            "#dc2626", "#fef2f2", "#fecaca")}
          {stat(f"{min_ct}d", "Fastest",        "#059669", "#f0fdf4", "#bbf7d0")}
          {stat(f"{max_ct}d", "Slowest",        "#d97706", "#fffbeb", "#fde68a")}
          {stat(len(ct_sorted), "Stories Tracked", "#374151", "#f8fafc", "#e2e8f0")}
        </div>'''

        # Bucket distribution chart
        BUCKETS = [(0,5,'0–5 days'),(5,10,'5–10 days'),(10,15,'10–15 days'),(15,20,'15–20 days'),(20,30,'20–30 days'),(30,99999,'30+ days')]
        bucket_data = [(label, sum(1 for t in ct_sorted if lo <= t < hi)) for lo,hi,label in BUCKETS]
        max_count = max((c for _,c in bucket_data), default=1) or 1

        bucket_rows = ''
        for label, count in bucket_data:
            bar_w = int(count / max_count * 220) if max_count else 0
            pct   = round(count / len(ct_sorted) * 100) if ct_sorted else 0
            bucket_rows += f'''<tr>
              <td style="padding:7px 10px 7px 0;font-size:13px;color:#374151;font-family:Arial;white-space:nowrap;width:95px">{label}</td>
              <td style="padding:7px 8px;width:230px">
                <svg width="230" height="20" viewBox="0 0 230 20" style="-webkit-print-color-adjust:exact;print-color-adjust:exact">
                  <rect width="230" height="20" rx="5" fill="#f1f5f9"/>
                  <rect width="{bar_w}" height="20" rx="5" fill="#8b5cf6" style="-webkit-print-color-adjust:exact;print-color-adjust:exact"/>
                </svg>
              </td>
              <td style="padding:7px 0 7px 10px;font-size:13px;font-weight:700;color:#7c3aed;font-family:Arial;width:35px">{count}</td>
              <td style="padding:7px 0;font-size:12px;color:#94a3b8;font-family:Arial">{pct}%</td>
            </tr>'''

        html += f'''<div style="display:flex;gap:1.5rem;flex-wrap:wrap;margin-bottom:1rem">
          <div style="flex:1;min-width:300px;background:#f8fafc;border-radius:12px;padding:1.2rem;border:1px solid #e2e8f0;-webkit-print-color-adjust:exact;print-color-adjust:exact">
            <div style="font-size:12px;font-weight:700;color:#1e293b;font-family:Arial;text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px">📊 Cycle Time Distribution (Dev Start → UAT Date)</div>
            <table style="width:100%;border-collapse:collapse">{bucket_rows}</table>
          </div>
        </div>'''

        # Per-story breakdown table (top 10 slowest)
        slowest = sorted(cycle_times, key=lambda x: -x['days'])[:10]
        story_rows = ''
        for i, t in enumerate(slowest):
            bg = '#f8fafc' if i % 2 == 0 else '#fff'
            ct_color = '#059669' if t['days'] <= 5 else '#d97706' if t['days'] <= 15 else '#dc2626'
            story_rows += f'''<tr style="background:{bg};-webkit-print-color-adjust:exact;print-color-adjust:exact">
              <td style="padding:7px 10px;color:#1d4ed8;font-weight:600;font-family:Arial;font-size:12px;white-space:nowrap">{t.get('key','—')}</td>
              <td style="padding:7px 10px;color:#1e293b;font-family:Arial;font-size:12px;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{str(t.get('summary','—'))[:55]}</td>
              <td style="padding:7px 10px;text-align:center;color:#374151;font-family:Arial;font-size:12px">{t.get('points','—')}</td>
              <td style="padding:7px 10px;text-align:center;font-weight:700;color:{ct_color};font-family:Arial;font-size:13px">{t['days']}d</td>
            </tr>'''

        html += f'''<div style="margin-top:1rem">
          <div style="font-size:12px;font-weight:700;color:#1e293b;font-family:Arial;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px">🐢 Top 10 Slowest Stories</div>
          <table style="width:100%;border-collapse:collapse;font-family:Arial">
            <thead><tr style="background:#1e3a8a;-webkit-print-color-adjust:exact;print-color-adjust:exact">
              <th style="padding:8px 10px;text-align:left;color:#fff;font-size:11px">Key</th>
              <th style="padding:8px 10px;text-align:left;color:#fff;font-size:11px">Summary</th>
              <th style="padding:8px 10px;text-align:center;color:#fff;font-size:11px">Points</th>
              <th style="padding:8px 10px;text-align:center;color:#fff;font-size:11px">Cycle Time</th>
            </tr></thead>
            <tbody>{story_rows}</tbody>
          </table>
        </div>'''

        # Missing dates warning
        missing = d.get('missing_dates', [])
        if missing:
            html += f'''<div style="background:#fefce8;border:1px solid #fde68a;border-radius:10px;padding:10px 14px;font-size:12px;color:#713f12;font-family:Arial;margin-top:1rem;-webkit-print-color-adjust:exact;print-color-adjust:exact">
              ⚠️ <strong>{len(missing)} tickets skipped</strong> — missing date fields:
              <span style="color:#92400e">{', '.join(set(m['missing'] for m in missing))}</span>.
              Tickets: {', '.join(m['key'] for m in missing[:8])}{' ...' if len(missing) > 8 else ''}
            </div>'''

        html += f'''<div style="background:#f8fafc;border-radius:10px;padding:10px 14px;border:1px solid #e2e8f0;font-size:12px;color:#64748b;font-family:Arial;margin-top:1rem">
          <strong style="color:#374151">Cycle Time</strong> = Dev Start → UAT Date &nbsp;|&nbsp;
          🟢 &lt;5d Fast &nbsp; 🟡 5–15d Normal &nbsp; 🔴 &gt;15d Slow
        </div>'''
    else:
        missing = d.get('missing_dates', [])
        html += f'''<div style="background:#fefce8;border:1px solid #fde68a;border-radius:10px;padding:12px 16px;font-size:13px;color:#713f12;font-family:Arial;-webkit-print-color-adjust:exact;print-color-adjust:exact">
          ⚠️ No Cycle Time data found for any ticket.<br>
          Make sure your Jira export has <strong>Dev Start</strong> and <strong>UAT Date</strong> columns filled in.<br>
          {f"<br>{len(missing)} tickets found but missing dates." if missing else ""}
        </div>'''


    # ── 4. BUG / DEFECT ANALYSIS ──────────────────────────────────────────────
    html += section_title('04', 'Bug / Defect Analysis')
    if d['bugs_total'] > 0:
        fix_rate    = round(d['bugs_done'] / d['bugs_total'] * 100)
        bug_density = round(d['bugs_total'] / d['total_pts'], 2) if d['total_pts'] else 'N/A'
        health, h_color, h_bg = (
            ('Excellent 🟢', '#065f46', '#d1fae5') if isinstance(bug_density, float) and bug_density < 0.1 else
            ('Acceptable 🟡', '#713f12', '#fef9c3') if isinstance(bug_density, float) and bug_density < 0.3 else
            ('Needs Attention 🔴', '#7f1d1d', '#fee2e2')
        )
        bug_seg = [('Fixed', d['bugs_done'], '#10b981'), ('Open', d['bugs_open'], '#ef4444')]
        html += f'''<div style="display:flex;gap:1.5rem;align-items:center;flex-wrap:wrap;margin-bottom:1rem">
          <div>{pie_chart(bug_seg, 120)}</div>
          <div style="flex:1;display:grid;grid-template-columns:1fr 1fr;gap:10px;min-width:220px">
            {stat(d['bugs_total'], 'Total Bugs', '#dc2626', '#fef2f2', '#fecaca')}
            {stat(d['bugs_done'],  'Fixed', '#059669', '#f0fdf4', '#bbf7d0')}
            {stat(d['bugs_open'],  'Open', '#d97706', '#fffbeb', '#fde68a')}
            {stat(f'{fix_rate}%', 'Fix Rate', '#1d4ed8', '#eff6ff', '#bfdbfe')}
          </div>
        </div>
        <div style="background:{h_bg};border-radius:10px;padding:10px 14px;font-size:13px;color:{h_color};font-family:Arial;-webkit-print-color-adjust:exact;print-color-adjust:exact">
          <strong>Bug Density:</strong> {bug_density} bugs/story point — Health: <strong>{health}</strong>
        </div>
        <div style="margin-top:10px">
          <div style="display:flex;justify-content:space-between;margin-bottom:6px;font-size:13px;font-family:Arial">
            <span style="color:#374151">Fix Rate Progress</span>
            <span style="font-weight:700;color:#059669">{fix_rate}%</span>
          </div>
          {prog_bar(fix_rate, '#10b981')}
        </div>'''
    else:
        html += '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:12px 16px;font-size:13px;color:#065f46;font-family:Arial;-webkit-print-color-adjust:exact;print-color-adjust:exact">🟢 No bugs or defects reported in this sprint. Excellent quality!</div>'

    # ── 5. EPIC / LABEL PROGRESS ──────────────────────────────────────────────
    html += section_title('05', 'Epic / Label Progress')
    if d['epics']:
        EPIC_COLORS = ['#3b82f6','#8b5cf6','#ec4899','#f59e0b','#10b981','#06b6d4','#f97316','#6366f1']
        html += '<table style="width:100%;border-collapse:collapse;font-family:Arial;font-size:13px">'
        html += '''<thead><tr style="background:#1e3a8a;-webkit-print-color-adjust:exact;print-color-adjust:exact">
          <th style="padding:10px;text-align:left;color:#fff;font-size:11px;text-transform:uppercase;letter-spacing:.05em">Epic / Label</th>
          <th style="padding:10px;text-align:center;color:#fff;font-size:11px;text-transform:uppercase">Done</th>
          <th style="padding:10px;text-align:center;color:#fff;font-size:11px;text-transform:uppercase">Total</th>
          <th style="padding:10px;text-align:center;color:#fff;font-size:11px;text-transform:uppercase">Pts Done</th>
          <th style="padding:10px;text-align:center;color:#fff;font-size:11px;text-transform:uppercase">Pts Total</th>
          <th style="padding:10px;text-align:left;color:#fff;font-size:11px;text-transform:uppercase">Progress</th>
        </tr></thead><tbody>'''
        for i, (ep, v) in enumerate(sorted(d['epics'].items(), key=lambda x: -x[1]['pts_total'])):
            pct    = round(v['done'] / v['total'] * 100) if v['total'] else 0
            color  = EPIC_COLORS[i % len(EPIC_COLORS)]
            bg     = '#f8fafc' if i % 2 == 0 else '#fff'
            p_color = '#059669' if pct == 100 else '#1d4ed8' if pct >= 50 else '#d97706'
            html += f'''<tr style="background:{bg};-webkit-print-color-adjust:exact;print-color-adjust:exact">
              <td style="padding:9px 10px;color:#1e293b;font-weight:500;border-bottom:1px solid #f1f5f9">
                <div style="display:flex;align-items:center;gap:8px">
                  <div style="width:10px;height:10px;border-radius:2px;background:{color};flex-shrink:0;-webkit-print-color-adjust:exact;print-color-adjust:exact"></div>
                  {ep[:40]}
                </div>
              </td>
              <td style="padding:9px 10px;text-align:center;color:#059669;font-weight:700;border-bottom:1px solid #f1f5f9">{v['done']}</td>
              <td style="padding:9px 10px;text-align:center;color:#374151;border-bottom:1px solid #f1f5f9">{v['total']}</td>
              <td style="padding:9px 10px;text-align:center;color:#059669;font-weight:700;border-bottom:1px solid #f1f5f9">{round(v['pts_done'])}</td>
              <td style="padding:9px 10px;text-align:center;color:#374151;border-bottom:1px solid #f1f5f9">{round(v['pts_total'])}</td>
              <td style="padding:9px 10px;border-bottom:1px solid #f1f5f9;min-width:140px">
                <div style="display:flex;align-items:center;gap:8px">
                  {prog_bar(pct, color, 100, 8)}
                  <span style="font-size:12px;font-weight:700;color:{p_color};font-family:Arial;white-space:nowrap">{pct}%</span>
                </div>
              </td>
            </tr>'''
        html += '</tbody></table>'
    else:
        html += '<div style="background:#fefce8;border:1px solid #fde68a;border-radius:10px;padding:12px 16px;font-size:13px;color:#713f12;font-family:Arial">Add <strong>Epic Name</strong> or <strong>Labels</strong> column to your Jira export to see epic-wise progress.</div>'

    # ── 6. INCOMPLETE ITEMS ───────────────────────────────────────────────────
    html += f'''<div class="page-break"></div>'''
    html += section_title('06', f'Incomplete Items ({len(d["incomplete"])})')
    if d['incomplete']:
        open_pts = round(sum(float(t.get('points') or 0) for t in d['incomplete']))
        html += f'<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:10px 14px;font-size:13px;color:#7f1d1d;font-family:Arial;margin-bottom:1rem;-webkit-print-color-adjust:exact;print-color-adjust:exact">⚠️ <strong>{len(d["incomplete"])} tickets</strong> not completed — <strong>{open_pts} story points</strong> carried over to next sprint.</div>'
        html += '<table style="width:100%;border-collapse:collapse;font-family:Arial;font-size:12px">'
        html += '''<thead><tr style="background:#1e3a8a;-webkit-print-color-adjust:exact;print-color-adjust:exact">
          <th style="padding:8px 10px;text-align:left;color:#fff;font-size:11px">Key</th>
          <th style="padding:8px 10px;text-align:left;color:#fff;font-size:11px">Summary</th>
          <th style="padding:8px 10px;text-align:left;color:#fff;font-size:11px">Type</th>
          <th style="padding:8px 10px;text-align:left;color:#fff;font-size:11px">Status</th>
          <th style="padding:8px 10px;text-align:center;color:#fff;font-size:11px">Points</th>
          <th style="padding:8px 10px;text-align:left;color:#fff;font-size:11px">Assignee</th>
        </tr></thead><tbody>'''
        for i, t in enumerate(d['incomplete']):
            bg       = '#fafafa' if i % 2 == 0 else '#fff'
            status   = t.get('status') or 'To Do'
            s_color  = '#1d4ed8' if is_inprog(status) else '#64748b'
            t_color  = '#dc2626' if is_bug(t.get('type')) else '#374151'
            html += f'''<tr style="background:{bg};-webkit-print-color-adjust:exact;print-color-adjust:exact">
              <td style="padding:7px 10px;color:#1d4ed8;font-weight:600;border-bottom:1px solid #f1f5f9;white-space:nowrap">{t.get('key','—')}</td>
              <td style="padding:7px 10px;color:#1e293b;border-bottom:1px solid #f1f5f9;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{(t.get('summary') or '—')[:55]}</td>
              <td style="padding:7px 10px;color:{t_color};border-bottom:1px solid #f1f5f9;white-space:nowrap">{t.get('type','—')}</td>
              <td style="padding:7px 10px;color:{s_color};border-bottom:1px solid #f1f5f9;white-space:nowrap;font-weight:500">{status}</td>
              <td style="padding:7px 10px;text-align:center;color:#374151;font-weight:600;border-bottom:1px solid #f1f5f9">{t.get('points','—')}</td>
              <td style="padding:7px 10px;color:#64748b;border-bottom:1px solid #f1f5f9;white-space:nowrap">{t.get('assignee','Unassigned')}</td>
            </tr>'''
        html += '</tbody></table>'
    else:
        html += '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:12px 16px;font-size:13px;color:#065f46;font-family:Arial;-webkit-print-color-adjust:exact;print-color-adjust:exact">🎉 All tickets completed! Perfect sprint delivery.</div>'

    # ── FOOTER ────────────────────────────────────────────────────────────────
    html += f'''
<div style="margin-top:2.5rem;padding-top:1rem;border-top:2px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
  <div style="font-size:11px;color:#94a3b8;font-family:Arial">{sprint} · {team}</div>
  <div style="font-size:11px;color:#94a3b8;font-family:Arial">Generated {now}</div>
  <div style="background:linear-gradient(135deg,#1e3a8a,#0ea5e9);border-radius:6px;padding:4px 12px;font-size:11px;color:#fff;font-family:Arial;font-weight:600;-webkit-print-color-adjust:exact;print-color-adjust:exact">Sprint Report</div>
</div>'''

    return html


# ── API ───────────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Sprint Report API is running"})


@app.route("/generate-report", methods=["POST"])
def generate_report():
    try:
        body    = request.get_json()
        meta    = {k: body.get(k, '') for k in ['sprint','dates','team','scrum_master','goal','notes']}
        tickets = body.get("tickets", [])
        # Debug: print first ticket date fields
        if tickets:
            t = tickets[0]
            print(f"DEBUG first ticket: key={t.get('key')} dev_start={repr(t.get('dev_start'))} uat_date={repr(t.get('uat_date'))} status={repr(t.get('status'))}")
        data    = analyse(tickets, meta)
        html    = build_html(data)
        return jsonify({"success": True, "html": html})
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "trace": traceback.format_exc()}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
