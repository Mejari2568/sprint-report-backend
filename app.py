import os
import json
import anthropic
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # allows requests from your GitHub Pages frontend

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


@app.route("/", methods=["GET"])a
def health():
    return jsonify({"status": "ok", "message": "Sprint Report API is running"})


@app.route("/generate-report", methods=["POST"])
def generate_report():
    try:
        body = request.get_json()

        sprint   = body.get("sprint", "Current Sprint")
        dates    = body.get("dates", "")
        team     = body.get("team", "")
        sm       = body.get("scrum_master", "")
        goal     = body.get("goal", "")
        notes    = body.get("notes", "")
        sections = body.get("sections", [])
        tickets  = body.get("tickets", [])  # parsed Excel rows from frontend

        data_context = build_data_context(tickets)

        prompt = f"""You are a senior Scrum Master generating a professional sprint report.
Return ONLY valid HTML content (no markdown, no code fences, no DOCTYPE) that goes inside a styled report container.

Use ONLY these HTML elements and classes:
- <h1> for report title (can contain <em>)
- <div class="report-meta"> with <div class="report-meta-item"><span class="k">label</span><span class="v">value</span></div>
- <div class="report-divider"></div> for section dividers
- <h2> for section headings
- <h3> for sub-headings
- <p> for paragraph text
- <ul><li> for bullet lists
- <div class="rep-stats"> with <div class="rep-stat"><div class="rv">VALUE</div><div class="rl">LABEL</div></div>
- <table class="rep-table"><thead><tr><th></th></tr></thead><tbody><tr><td></td></tr></tbody></table>
- <div class="highlight-box"> for positive callouts
- <div class="warn-box"> for warnings or blockers
- <span class="badge b-done">, <span class="badge b-bug">, <span class="badge b-prog">, <span class="badge b-todo">

SPRINT METADATA:
Sprint: {sprint} | Dates: {dates} | Team: {team} | Scrum Master: {sm}
Goal: {goal}
Notes: {notes}

{data_context}

SECTIONS TO INCLUDE: {', '.join(sections)}

Generate a thorough, accurate, stakeholder-ready sprint report. Use the data accurately.
Be specific with numbers. Make it professional and insightful.
Start directly with the <h1> tag."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )

        html = message.content[0].text.replace("```html", "").replace("```", "").strip()
        return jsonify({"success": True, "html": html})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def build_data_context(tickets):
    if not tickets:
        return "No ticket data provided — generate report from metadata only."

    total  = len(tickets)
    done   = [t for t in tickets if (t.get("status") or "").lower().strip() == "done"]
    inprog = [t for t in tickets if "progress" in (t.get("status") or "").lower()]
    todo   = [t for t in tickets if (t.get("status") or "").lower().strip() in ["to do", "todo"]]
    bugs   = [t for t in tickets if (t.get("type") or "").lower() == "bug"]
    bugs_done = [b for b in bugs if (b.get("status") or "").lower().strip() == "done"]

    pts      = sum(float(t.get("points") or 0) for t in tickets)
    done_pts = sum(float(t.get("points") or 0) for t in done)
    pct      = round(done_pts / pts * 100) if pts else 0

    assignee_map = {}
    for t in tickets:
        a = t.get("assignee") or "Unassigned"
        if a not in assignee_map:
            assignee_map[a] = {"done": 0, "total": 0, "pts": 0}
        assignee_map[a]["total"] += 1
        if (t.get("status") or "").lower().strip() == "done":
            assignee_map[a]["done"] += 1
            assignee_map[a]["pts"] += float(t.get("points") or 0)

    epic_map = {}
    for t in tickets:
        ep = t.get("epic") or "No Epic"
        if ep not in epic_map:
            epic_map[ep] = {"done": 0, "total": 0}
        epic_map[ep]["total"] += 1
        if (t.get("status") or "").lower().strip() == "done":
            epic_map[ep]["done"] += 1

    incomplete = "\n".join(
        f"- {t.get('summary')} [{t.get('status')}] | {t.get('points') or 0}pts | {t.get('assignee') or '?'} | {t.get('type') or '?'}"
        for t in tickets if (t.get("status") or "").lower().strip() != "done"
    ) or "All items completed!"

    completed_sample = "\n".join(
        f"- {t.get('summary')} | {t.get('points') or 0}pts | {t.get('assignee') or '?'}"
        for t in done[:20]
    )

    assignee_lines = "\n".join(
        f"  {a}: {v['done']}/{v['total']} tickets, {round(v['pts'])} pts"
        for a, v in assignee_map.items()
    )
    epic_lines = "\n".join(
        f"  {ep}: {v['done']}/{v['total']} done"
        for ep, v in epic_map.items()
    )

    return f"""SPRINT DATA ({total} tickets from Jira export):
Status: {len(done)} Done, {len(inprog)} In Progress, {len(todo)} To Do
Story points: {round(done_pts)} completed / {round(pts)} committed ({pct}% completion)
Bugs: {len(bugs)} total, {len(bugs_done)} resolved, {len(bugs) - len(bugs_done)} open

Assignee breakdown:
{assignee_lines}

Epic breakdown:
{epic_lines}

Completed items (sample):
{completed_sample}

Incomplete items:
{incomplete}"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
