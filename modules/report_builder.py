from datetime import datetime
from config import EPIC_COLORS
from modules.analyser import is_done, is_inprog, is_bug
from modules.chart_utils import (
    donut_chart, progress_bar, horizontal_bar_chart,
    pie_chart, bucket_bar
)


# ── Reusable HTML helpers ─────────────────────────────────────────────────────
def stat_card(val, label, color='#1e293b', bg='#f8fafc', border='#e2e8f0'):
    return f'''<div style="background:{bg};border:1.5px solid {border};border-radius:12px;
        padding:16px;text-align:center;-webkit-print-color-adjust:exact;print-color-adjust:exact">
  <div style="font-size:28px;font-weight:700;color:{color};font-family:Arial">{val}</div>
  <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.05em;
              margin-top:4px;font-family:Arial">{label}</div>
</div>'''


def section_title(num, title):
    return f'''<div style="display:flex;align-items:center;gap:12px;margin:2.5rem 0 1.2rem;page-break-inside:avoid">
  <div style="background:#1e40af;color:#fff;border-radius:8px;width:28px;height:28px;
              display:flex;align-items:center;justify-content:center;font-size:12px;
              font-weight:700;font-family:Arial;flex-shrink:0;
              -webkit-print-color-adjust:exact;print-color-adjust:exact">{num}</div>
  <h2 style="font-size:15px;font-weight:700;color:#1e293b;font-family:Arial;margin:0;
             text-transform:uppercase;letter-spacing:.06em">{title}</h2>
  <div style="flex:1;height:1.5px;background:linear-gradient(to right,#3b82f6,transparent);
              -webkit-print-color-adjust:exact;print-color-adjust:exact"></div>
</div>'''


def divider():
    return '<div style="height:1px;background:rgba(255,255,255,0.07);margin:1.5rem 0"></div>'


def info_box(text, color='blue'):
    styles = {
        'blue':   ('#eff6ff', '#bfdbfe', '#1d4ed8'),
        'green':  ('#f0fdf4', '#bbf7d0', '#065f46'),
        'yellow': ('#fefce8', '#fde68a', '#713f12'),
        'red':    ('#fef2f2', '#fecaca', '#7f1d1d'),
    }
    bg, border, text_color = styles.get(color, styles['blue'])
    return f'''<div style="background:{bg};border:1px solid {border};border-radius:10px;
        padding:10px 14px;font-size:13px;color:{text_color};font-family:Arial;
        -webkit-print-color-adjust:exact;print-color-adjust:exact">{text}</div>'''


# ── Report Sections ───────────────────────────────────────────────────────────
def build_header(d):
    meta   = d['meta']
    sprint = meta.get('sprint', 'Sprint')
    team   = meta.get('team', '')
    sm     = meta.get('scrum_master', '')
    dates  = meta.get('dates', '')
    goal   = meta.get('goal', '')
    now    = datetime.now().strftime('%d %b %Y, %H:%M')

    return f'''
<div style="background:linear-gradient(135deg,#1e3a8a 0%,#1d4ed8 60%,#0ea5e9 100%);
            border-radius:16px;padding:2.5rem 2rem;margin-bottom:2rem;
            -webkit-print-color-adjust:exact;print-color-adjust:exact">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:1rem">
    <div>
      <div style="font-size:11px;color:rgba(255,255,255,0.65);letter-spacing:.15em;
                  text-transform:uppercase;font-family:Arial;margin-bottom:8px">Sprint Report</div>
      <h1 style="font-family:Arial;font-size:2rem;font-weight:800;color:#fff;margin-bottom:6px">{sprint}</h1>
      {'<div style="font-size:14px;color:rgba(255,255,255,0.8);font-family:Arial">' + team + '</div>' if team else ''}
    </div>
    <div style="text-align:right">
      {'<div style="font-size:13px;color:rgba(255,255,255,0.75);font-family:Arial">📅 ' + dates + '</div>' if dates else ''}
      {'<div style="font-size:13px;color:rgba(255,255,255,0.75);font-family:Arial;margin-top:4px">👤 ' + sm + '</div>' if sm else ''}
      <div style="font-size:11px;color:rgba(255,255,255,0.5);font-family:Arial;margin-top:8px">Generated {now}</div>
    </div>
  </div>
  {'<div style="margin-top:1.2rem;background:rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;font-size:13px;color:rgba(255,255,255,0.9);font-family:Arial;border-left:3px solid rgba(255,255,255,0.4)"><strong>Goal:</strong> ' + goal + '</div>' if goal else ''}
</div>'''


def build_sprint_summary(d):
    notes      = d['meta'].get('notes', '')
    completion = d['completion']
    html = section_title('01', 'Sprint Summary')
    html += f'''<div style="display:flex;gap:1.5rem;align-items:center;flex-wrap:wrap;margin-bottom:1.5rem">
  <div style="flex-shrink:0">{donut_chart(d['done'], d['inprog'], d['todo'])}</div>
  <div style="flex:1;min-width:220px">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      {stat_card(d['total'],  'Total Tickets', '#1e293b')}
      {stat_card(d['done'],   'Completed',     '#059669', '#f0fdf4', '#bbf7d0')}
      {stat_card(d['inprog'], 'In Progress',   '#1d4ed8', '#eff6ff', '#bfdbfe')}
      {stat_card(d['todo'],   'To Do',         '#64748b', '#f8fafc', '#e2e8f0')}
    </div>
  </div>
</div>
<div style="background:#f8fafc;border-radius:12px;padding:1.2rem;border:1px solid #e2e8f0;
            margin-bottom:1rem;-webkit-print-color-adjust:exact;print-color-adjust:exact">
  <div style="display:flex;justify-content:space-between;margin-bottom:8px">
    <span style="font-size:14px;font-weight:600;color:#1e293b;font-family:Arial">Story Points Progress</span>
    <span style="font-size:14px;font-weight:700;color:#059669;font-family:Arial">
      {d['done_pts']} / {d['total_pts']} pts ({completion}%)
    </span>
  </div>
  {progress_bar(completion)}
  <div style="display:flex;gap:1.5rem;margin-top:10px;font-size:12px;font-family:Arial;flex-wrap:wrap">
    <span style="color:#059669">✅ Done: <strong>{d['done_pts']} pts</strong></span>
    <span style="color:#1d4ed8">🔵 In Progress: <strong>{d['inprog_pts']} pts</strong></span>
    <span style="color:#64748b">⚪ To Do: <strong>{d['todo_pts']} pts</strong></span>
  </div>
</div>'''
    if notes:
        html += info_box(f'⚠️ <strong>Notes:</strong> {notes}', 'yellow')
    return html


def build_status_breakdown(d):
    html  = section_title('02', 'Ticket Status Breakdown')
    items = [
        ('Done',        d['done'],   '#10b981'),
        ('In Progress', d['inprog'], '#3b82f6'),
        ('To Do',       d['todo'],   '#94a3b8'),
    ]
    max_s = max(d['done'], d['inprog'], d['todo'], 1)
    html += f'''<div style="display:flex;gap:2rem;align-items:center;flex-wrap:wrap;margin-bottom:1rem">
  <div>{horizontal_bar_chart(items, max_s)}</div>
  <div style="display:flex;flex-direction:column;gap:8px">'''
    for label, val, color in items:
        pct = round(val / d['total'] * 100) if d['total'] else 0
        html += f'''<div style="display:flex;align-items:center;gap:8px;font-family:Arial;font-size:13px">
      <div style="width:12px;height:12px;border-radius:3px;background:{color};
                  -webkit-print-color-adjust:exact;print-color-adjust:exact"></div>
      <span style="color:#374151">{label}: <strong>{val}</strong> ({pct}%)</span>
    </div>'''
    html += '</div></div>'
    return html


def build_cycle_time(d):
    html        = section_title('03', 'Cycle Time Analysis')
    cycle_times = d.get('cycle_times', [])
    cycle_days  = [c['days'] for c in cycle_times]

    if not cycle_days:
        missing = d.get('missing_dates', [])
        html += info_box(
            f'⚠️ No Cycle Time data found. Make sure your Jira export has <strong>Dev Start</strong> '
            f'and <strong>UAT Date</strong> columns filled in.'
            + (f'<br>{len(missing)} tickets found but missing dates.' if missing else ''),
            'yellow'
        )
        return html

    avg_ct = d['avg_cycle']
    p50    = d['p50']
    p90    = d['p90']
    min_ct = d['min_ct']
    max_ct = d['max_ct']

    # KPI cards
    html += f'''<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:1.5rem">
  {stat_card(f"{avg_ct}d", "Avg Cycle Time", "#7c3aed", "#f5f3ff", "#ddd6fe")}
  {stat_card(f"{p50}d",    "Median (P50)",   "#0369a1", "#f0f9ff", "#bae6fd")}
  {stat_card(f"{p90}d",    "P90",            "#dc2626", "#fef2f2", "#fecaca")}
  {stat_card(f"{min_ct}d", "Fastest",        "#059669", "#f0fdf4", "#bbf7d0")}
  {stat_card(f"{max_ct}d", "Slowest",        "#d97706", "#fffbeb", "#fde68a")}
  {stat_card(len(cycle_days), "Stories Tracked", "#374151", "#f8fafc", "#e2e8f0")}
</div>'''

    # Bucket chart
    buckets   = d.get('cycle_buckets', [])
    max_count = max((c for _, c in buckets), default=1) or 1
    rows = ''.join(bucket_bar(label, count, max_count, '#8b5cf6', len(cycle_days))
                   for label, count in buckets)
    html += f'''<div style="background:#f8fafc;border-radius:12px;padding:1.2rem;
        border:1px solid #e2e8f0;margin-bottom:1rem;
        -webkit-print-color-adjust:exact;print-color-adjust:exact">
  <div style="font-size:12px;font-weight:700;color:#1e293b;font-family:Arial;
              text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px">
    📊 Cycle Time Distribution (Dev Start → UAT Date)
  </div>
  <table style="width:100%;border-collapse:collapse">{rows}</table>
</div>'''

    # Top 10 slowest stories
    slowest   = sorted(cycle_times, key=lambda x: -x['days'])[:10]
    story_rows = ''
    for i, t in enumerate(slowest):
        bg       = '#f8fafc' if i % 2 == 0 else '#fff'
        ct_color = '#059669' if t['days'] <= 5 else '#d97706' if t['days'] <= 15 else '#dc2626'
        story_rows += f'''<tr style="background:{bg};-webkit-print-color-adjust:exact;print-color-adjust:exact">
      <td style="padding:7px 10px;color:#1d4ed8;font-weight:600;font-family:Arial;font-size:12px">{t.get('key','—')}</td>
      <td style="padding:7px 10px;color:#1e293b;font-family:Arial;font-size:12px;
                 max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{str(t.get('summary','—'))[:55]}</td>
      <td style="padding:7px 10px;text-align:center;color:#374151;font-family:Arial;font-size:12px">{t.get('points','—')}</td>
      <td style="padding:7px 10px;text-align:center;font-weight:700;color:{ct_color};font-family:Arial;font-size:13px">{t['days']}d</td>
    </tr>'''

    html += f'''<div style="margin-top:1rem">
  <div style="font-size:12px;font-weight:700;color:#1e293b;font-family:Arial;
              text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px">🐢 Top 10 Slowest Stories</div>
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
        html += f'''<div style="background:#fefce8;border:1px solid #fde68a;border-radius:10px;
            padding:10px 14px;font-size:12px;color:#713f12;font-family:Arial;margin-top:1rem;
            -webkit-print-color-adjust:exact;print-color-adjust:exact">
  ⚠️ <strong>{len(missing)} tickets skipped</strong> — missing:
  {', '.join(set(m['missing'] for m in missing))}.
  Tickets: {', '.join(m['key'] for m in missing[:8])}{' ...' if len(missing) > 8 else ''}
</div>'''

    html += info_box(
        '<strong>Cycle Time</strong> = Dev Start → UAT Date &nbsp;|&nbsp; '
        '🟢 &lt;5d Fast &nbsp; 🟡 5–15d Normal &nbsp; 🔴 &gt;15d Slow',
        'blue'
    )
    return html


def build_bug_analysis(d):
    html = section_title('04', 'Bug / Defect Analysis')
    if d['bugs_total'] == 0:
        html += info_box('🟢 No bugs or defects reported in this sprint. Excellent quality!', 'green')
        return html

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
    {stat_card(d['bugs_total'], 'Total Bugs', '#dc2626', '#fef2f2', '#fecaca')}
    {stat_card(d['bugs_done'],  'Fixed',      '#059669', '#f0fdf4', '#bbf7d0')}
    {stat_card(d['bugs_open'],  'Open',       '#d97706', '#fffbeb', '#fde68a')}
    {stat_card(f'{fix_rate}%', 'Fix Rate',   '#1d4ed8', '#eff6ff', '#bfdbfe')}
  </div>
</div>
<div style="background:{h_bg};border-radius:10px;padding:10px 14px;font-size:13px;
            color:{h_color};font-family:Arial;-webkit-print-color-adjust:exact;print-color-adjust:exact">
  <strong>Bug Density:</strong> {bug_density} bugs/story point — Health: <strong>{health}</strong>
</div>
<div style="margin-top:10px">
  <div style="display:flex;justify-content:space-between;margin-bottom:6px;font-size:13px;font-family:Arial">
    <span style="color:#374151">Fix Rate Progress</span>
    <span style="font-weight:700;color:#059669">{fix_rate}%</span>
  </div>
  {progress_bar(fix_rate, '#10b981')}
</div>'''
    return html


def build_epic_progress(d):
    """Epic section — wrapped in no-print so it's hidden in PDF."""
    html = '<div class="no-print">'
    html += section_title('05', 'Epic / Label Progress')

    if not d['epics']:
        html += info_box('Add <strong>Epic Name</strong> or <strong>Labels</strong> column to your Jira export.', 'yellow')
        html += '</div>'
        return html

    html += '<table style="width:100%;border-collapse:collapse;font-family:Arial;font-size:13px">'
    html += '''<thead><tr style="background:#1e3a8a;-webkit-print-color-adjust:exact;print-color-adjust:exact">
      <th style="padding:10px;text-align:left;color:#fff;font-size:11px;text-transform:uppercase">Epic / Label</th>
      <th style="padding:10px;text-align:center;color:#fff;font-size:11px">Done</th>
      <th style="padding:10px;text-align:center;color:#fff;font-size:11px">Total</th>
      <th style="padding:10px;text-align:center;color:#fff;font-size:11px">Pts Done</th>
      <th style="padding:10px;text-align:center;color:#fff;font-size:11px">Pts Total</th>
      <th style="padding:10px;text-align:left;color:#fff;font-size:11px">Progress</th>
    </tr></thead><tbody>'''

    for i, (ep, v) in enumerate(sorted(d['epics'].items(), key=lambda x: -x[1]['pts_total'])):
        pct     = round(v['done'] / v['total'] * 100) if v['total'] else 0
        color   = EPIC_COLORS[i % len(EPIC_COLORS)]
        bg      = '#f8fafc' if i % 2 == 0 else '#fff'
        p_color = '#059669' if pct == 100 else '#1d4ed8' if pct >= 50 else '#d97706'
        html += f'''<tr style="background:{bg};-webkit-print-color-adjust:exact;print-color-adjust:exact">
      <td style="padding:9px 10px;color:#1e293b;font-weight:500;border-bottom:1px solid #f1f5f9">
        <div style="display:flex;align-items:center;gap:8px">
          <div style="width:10px;height:10px;border-radius:2px;background:{color};flex-shrink:0;
                      -webkit-print-color-adjust:exact;print-color-adjust:exact"></div>
          {ep[:40]}
        </div>
      </td>
      <td style="padding:9px 10px;text-align:center;color:#059669;font-weight:700;border-bottom:1px solid #f1f5f9">{v['done']}</td>
      <td style="padding:9px 10px;text-align:center;color:#374151;border-bottom:1px solid #f1f5f9">{v['total']}</td>
      <td style="padding:9px 10px;text-align:center;color:#059669;font-weight:700;border-bottom:1px solid #f1f5f9">{round(v['pts_done'])}</td>
      <td style="padding:9px 10px;text-align:center;color:#374151;border-bottom:1px solid #f1f5f9">{round(v['pts_total'])}</td>
      <td style="padding:9px 10px;border-bottom:1px solid #f1f5f9;min-width:140px">
        <div style="display:flex;align-items:center;gap:8px">
          {progress_bar(pct, color, 100, 8)}
          <span style="font-size:12px;font-weight:700;color:{p_color};font-family:Arial;white-space:nowrap">{pct}%</span>
        </div>
      </td>
    </tr>'''

    html += '</tbody></table></div>'
    return html


def build_qa_bugs(d):
    html          = section_title('06', 'QA Bugs Per Story')
    qa_bugs       = d.get('qa_bugs', [])
    stories       = d.get('stories', [])
    story_bug_map = d.get('story_bug_map', {})

    if not qa_bugs:
        html += info_box('⚠️ Upload the QA Bugs Excel file to see bug counts per story.', 'yellow')
        return html

    total_qa = len(qa_bugs)
    qa_done  = sum(1 for b in qa_bugs if is_done(b.get('status')))
    qa_open  = total_qa - qa_done
    unlinked = story_bug_map.get('__unlinked__', [])
    avg_bugs = round(total_qa / len(stories), 1) if stories else 0

    html += f'''<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:1.5rem">
  {stat_card(total_qa,  'Total QA Bugs',  '#dc2626', '#fef2f2', '#fecaca')}
  {stat_card(qa_done,   'Fixed',          '#059669', '#f0fdf4', '#bbf7d0')}
  {stat_card(qa_open,   'Open',           '#d97706', '#fffbeb', '#fde68a')}
  {stat_card(avg_bugs,  'Bugs/Story Avg', '#7c3aed', '#f5f3ff', '#ddd6fe')}
  {stat_card(len(unlinked), 'Unlinked Bugs', '#64748b', '#f8fafc', '#e2e8f0')}
</div>'''

    story_bug_counts = []
    for story in sorted(stories, key=lambda x: x.get('key', '')):
        sk   = story.get('key', '')
        sm   = (story.get('summary') or '')[:50]
        sp   = story.get('points', 0)
        bugs = story_bug_map.get(sk, [])
        bc   = len(bugs)
        bug_keys = ', '.join(b.get('key', '') for b in bugs[:5])
        story_bug_counts.append((sk, sm, sp, bc, bug_keys))

    story_bug_counts.sort(key=lambda x: -x[3])
    story_rows = ''
    for i, (sk, sm, sp, bc, bug_keys) in enumerate(story_bug_counts):
        bg       = '#fef2f2' if bc > 2 else '#fffbeb' if bc > 0 else ('#f8fafc' if i % 2 == 0 else '#fff')
        bc_color = '#dc2626' if bc > 2 else '#d97706' if bc > 0 else '#059669'
        bc_label = f'<strong style="color:{bc_color}">{bc}</strong>' if bc > 0 else '<span style="color:#059669">0 ✅</span>'
        story_rows += f'''<tr style="background:{bg};-webkit-print-color-adjust:exact;print-color-adjust:exact">
      <td style="padding:7px 10px;color:#1d4ed8;font-weight:600;font-family:Arial;font-size:12px;white-space:nowrap">{sk}</td>
      <td style="padding:7px 10px;color:#1e293b;font-family:Arial;font-size:12px;
                 max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{sm}</td>
      <td style="padding:7px 10px;text-align:center;color:#374151;font-family:Arial;font-size:12px">{sp}</td>
      <td style="padding:7px 10px;text-align:center;font-family:Arial;font-size:13px">{bc_label}</td>
      <td style="padding:7px 10px;font-family:Arial;font-size:11px;color:#64748b">{bug_keys}</td>
    </tr>'''

    html += f'''<table style="width:100%;border-collapse:collapse;font-family:Arial">
  <thead><tr style="background:#1e3a8a;-webkit-print-color-adjust:exact;print-color-adjust:exact">
    <th style="padding:8px 10px;text-align:left;color:#fff;font-size:11px">Story Key</th>
    <th style="padding:8px 10px;text-align:left;color:#fff;font-size:11px">Summary</th>
    <th style="padding:8px 10px;text-align:center;color:#fff;font-size:11px">Story Pts</th>
    <th style="padding:8px 10px;text-align:center;color:#fff;font-size:11px">QA Bugs</th>
    <th style="padding:8px 10px;text-align:left;color:#fff;font-size:11px">Bug Keys</th>
  </tr></thead>
  <tbody>{story_rows}</tbody>
</table>'''

    if unlinked:
        ul_keys = ', '.join(b.get('key', '') for b in unlinked)
        html += info_box(f'⚠️ <strong>{len(unlinked)} bugs not linked</strong> to any sprint story: {ul_keys}', 'yellow')

    html += info_box(
        '🔴 &gt;2 bugs — High defect story &nbsp;|&nbsp; 🟡 1–2 bugs — Needs attention &nbsp;|&nbsp; 🟢 0 bugs — Clean delivery',
        'blue'
    )
    return html


def build_incomplete_items(d):
    html = '<div class="page-break"></div>'
    html += section_title('07', f'Incomplete Items ({len(d["incomplete"])})')

    if not d['incomplete']:
        html += info_box('🎉 All tickets completed! Perfect sprint delivery.', 'green')
        return html

    open_pts = round(sum(float(t.get('points') or 0) for t in d['incomplete']))
    html += info_box(
        f'⚠️ <strong>{len(d["incomplete"])} tickets</strong> not completed — '
        f'<strong>{open_pts} story points</strong> carried over to next sprint.',
        'red'
    )
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
        bg      = '#fafafa' if i % 2 == 0 else '#fff'
        status  = t.get('status') or 'To Do'
        s_color = '#1d4ed8' if is_inprog(status) else '#64748b'
        t_color = '#dc2626' if is_bug(t.get('type')) else '#374151'
        html += f'''<tr style="background:{bg};-webkit-print-color-adjust:exact;print-color-adjust:exact">
      <td style="padding:7px 10px;color:#1d4ed8;font-weight:600;border-bottom:1px solid #f1f5f9;white-space:nowrap">{t.get('key','—')}</td>
      <td style="padding:7px 10px;color:#1e293b;border-bottom:1px solid #f1f5f9;
                 max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{(t.get('summary') or '—')[:55]}</td>
      <td style="padding:7px 10px;color:{t_color};border-bottom:1px solid #f1f5f9;white-space:nowrap">{t.get('type','—')}</td>
      <td style="padding:7px 10px;color:{s_color};border-bottom:1px solid #f1f5f9;white-space:nowrap;font-weight:500">{status}</td>
      <td style="padding:7px 10px;text-align:center;color:#374151;font-weight:600;border-bottom:1px solid #f1f5f9">{t.get('points','—')}</td>
      <td style="padding:7px 10px;color:#64748b;border-bottom:1px solid #f1f5f9;white-space:nowrap">{t.get('assignee','Unassigned')}</td>
    </tr>'''

    html += '</tbody></table>'
    return html


def build_footer(d):
    meta  = d['meta']
    now   = datetime.now().strftime('%d %b %Y, %H:%M')
    return f'''
<div style="margin-top:2.5rem;padding-top:1rem;border-top:2px solid #e2e8f0;
            display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
  <div style="font-size:11px;color:#94a3b8;font-family:Arial">{meta.get('sprint','')} · {meta.get('team','')}</div>
  <div style="font-size:11px;color:#94a3b8;font-family:Arial">Generated {now}</div>
  <div style="background:linear-gradient(135deg,#1e3a8a,#0ea5e9);border-radius:6px;padding:4px 12px;
              font-size:11px;color:#fff;font-family:Arial;font-weight:600;
              -webkit-print-color-adjust:exact;print-color-adjust:exact">Sprint Report</div>
</div>'''


# ── Master build function ─────────────────────────────────────────────────────
def build_report(d):
    """Build the complete HTML report from analysed data."""
    sections = [
        '<style>* {{ box-sizing: border-box; margin: 0; padding: 0; }} '
        'body {{ background: #fff; }} '
        'table {{ border-collapse: collapse; width: 100%; }} '
        'th, td {{ font-family: Arial, sans-serif; }} '
        '@media print {{ '
        '  * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }} '
        '  .no-print {{ display: none !important; }} '
        '  .page-break {{ page-break-before: always; }} '
        '}}</style>',
        build_header(d),
        build_sprint_summary(d),
        build_status_breakdown(d),
        build_cycle_time(d),
        build_bug_analysis(d),
        build_epic_progress(d),
        build_qa_bugs(d),
        build_incomplete_items(d),
        build_footer(d),
    ]
    return '\n'.join(sections)
