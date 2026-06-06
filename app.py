import os
from flask import Flask, request, jsonify
from flask_cors import CORS

from modules.analyser import analyse
from modules.bug_analyser import analyse_bugs
from modules.report_builder import build_report

app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Sprint Report API is running"})


@app.route("/generate-report", methods=["POST"])
def generate_report():
    try:
        body        = request.get_json()
        meta        = {k: body.get(k, '') for k in ['sprint', 'dates', 'team', 'scrum_master', 'goal', 'notes']}
        tickets     = body.get("tickets", [])
        bug_tickets = body.get("bug_tickets", [])

        # Analyse sprint data
        data = analyse(tickets, meta)

        # Match QA bugs to stories via Linked Issues field
        if bug_tickets:
            story_bug_map         = analyse_bugs(bug_tickets, data['stories'])
            data['qa_bugs']       = bug_tickets
            data['story_bug_map'] = story_bug_map
        else:
            data['qa_bugs']       = []
            data['story_bug_map'] = {}

        html = build_report(data)
        return jsonify({"success": True, "html": html})

    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "trace": traceback.format_exc()}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
