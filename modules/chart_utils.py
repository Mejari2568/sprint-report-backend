import math


def donut_chart(done, inprog, todo, size=140):
    """Donut chart showing Done / In Progress / To Do split."""
    total = done + inprog + todo or 1
    cx = cy = size / 2
    r  = size / 2 - 14
    circ = 2 * math.pi * r
    done_pct  = round(done / total * 100)
    done_dash = done  / total * circ
    prog_dash = inprog / total * circ

    def arc(val, color, offset):
        dash = val / total * circ
        return (
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
            f'stroke-width="18" stroke-dasharray="{dash:.1f} {circ:.1f}" '
            f'stroke-dashoffset="-{offset:.1f}" stroke-linecap="butt" '
            f'style="-webkit-print-color-adjust:exact;print-color-adjust:exact"/>'
        )

    return f'''<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}"
      style="-webkit-print-color-adjust:exact;print-color-adjust:exact">
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#e8edf5" stroke-width="18"/>
  {arc(done,   "#10b981", 0)}
  {arc(inprog, "#3b82f6", done_dash)}
  {arc(todo,   "#e2e8f0", done_dash + prog_dash)}
  <text x="{cx}" y="{cy - 6}" text-anchor="middle" font-size="20" font-weight="700"
        fill="#1e293b" font-family="Arial">{done_pct}%</text>
  <text x="{cx}" y="{cy + 14}" text-anchor="middle" font-size="10"
        fill="#64748b" font-family="Arial">Done</text>
</svg>'''


def progress_bar(pct, color='#10b981', w=400, h=10):
    """Horizontal SVG progress bar — print safe."""
    fill_w = int(pct / 100 * w)
    return f'''<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}"
      style="max-width:100%;-webkit-print-color-adjust:exact;print-color-adjust:exact">
  <rect width="{w}" height="{h}" rx="5" fill="#e2e8f0"/>
  <rect width="{fill_w}" height="{h}" rx="5" fill="{color}"
        style="-webkit-print-color-adjust:exact;print-color-adjust:exact"/>
</svg>'''


def horizontal_bar_chart(items, max_val, label_w=130, bar_area=260):
    """
    Horizontal bar chart.
    items = list of (label, value, color)
    """
    bar_h = 28
    gap   = 10
    total_h = len(items) * (bar_h + gap) + 10
    width = label_w + bar_area + 60

    svg = (
        f'<svg width="{width}" height="{total_h}" viewBox="0 0 {width} {total_h}" '
        f'style="-webkit-print-color-adjust:exact;print-color-adjust:exact" font-family="Arial">'
    )
    for i, (label, val, color) in enumerate(items):
        y     = i * (bar_h + gap)
        bar_w = int((val / max_val) * bar_area) if max_val else 0
        svg += f'''
  <text x="0" y="{y + bar_h - 8}" font-size="12" fill="#374151" font-weight="500">{label[:18]}</text>
  <rect x="{label_w}" y="{y + 4}" width="{bar_area}" height="{bar_h - 8}" rx="4" fill="#f1f5f9"
        style="-webkit-print-color-adjust:exact;print-color-adjust:exact"/>
  <rect x="{label_w}" y="{y + 4}" width="{bar_w}" height="{bar_h - 8}" rx="4" fill="{color}"
        style="-webkit-print-color-adjust:exact;print-color-adjust:exact"/>
  <text x="{label_w + bar_w + 8}" y="{y + bar_h - 8}" font-size="12" fill="#374151" font-weight="600">{val}</text>'''
    svg += '</svg>'
    return svg


def pie_chart(segments, size=160):
    """
    Pie chart.
    segments = list of (label, value, color)
    """
    total = sum(v for _, v, _ in segments) or 1
    cx = cy = size / 2
    r  = size / 2 - 10
    svg = (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
        f'style="-webkit-print-color-adjust:exact;print-color-adjust:exact">'
    )
    angle = -math.pi / 2
    for _, val, color in segments:
        if val == 0:
            continue
        sweep = 2 * math.pi * val / total
        x1 = cx + r * math.cos(angle)
        y1 = cy + r * math.sin(angle)
        x2 = cx + r * math.cos(angle + sweep)
        y2 = cy + r * math.sin(angle + sweep)
        large = 1 if sweep > math.pi else 0
        svg += (
            f'<path d="M{cx},{cy} L{x1:.1f},{y1:.1f} A{r},{r} 0 {large},1 '
            f'{x2:.1f},{y2:.1f} Z" fill="{color}" '
            f'style="-webkit-print-color-adjust:exact;print-color-adjust:exact"/>'
        )
        angle += sweep
    svg += '</svg>'
    return svg


def bucket_bar(label, count, max_count, color, total):
    """Single bucket row with SVG bar for distribution charts."""
    bar_w = int(count / max_count * 220) if max_count else 0
    pct   = round(count / total * 100) if total else 0
    return f'''<tr>
  <td style="padding:7px 10px 7px 0;font-size:13px;color:#374151;font-family:Arial;white-space:nowrap;width:95px">{label}</td>
  <td style="padding:7px 8px;width:230px">
    <svg width="230" height="20" viewBox="0 0 230 20"
         style="-webkit-print-color-adjust:exact;print-color-adjust:exact">
      <rect width="230" height="20" rx="5" fill="#f1f5f9"/>
      <rect width="{bar_w}" height="20" rx="5" fill="{color}"
            style="-webkit-print-color-adjust:exact;print-color-adjust:exact"/>
    </svg>
  </td>
  <td style="padding:7px 0 7px 10px;font-size:13px;font-weight:700;color:{color};font-family:Arial;width:35px">{count}</td>
  <td style="padding:7px 0;font-size:12px;color:#94a3b8;font-family:Arial">{pct}%</td>
</tr>'''
