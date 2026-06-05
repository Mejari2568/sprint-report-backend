import re
from collections import defaultdict


def analyse_bugs(bug_tickets, story_tickets):
    """
    Match bugs to stories via the Linked Issues field.
    Extracts story keys like CT-101 from linked issues text
    and maps each bug to its parent story.

    Returns: dict { story_key: [bug, ...], '__unlinked__': [bug, ...] }
    """
    story_map     = {t.get('key', '').strip(): t for t in story_tickets if t.get('key')}
    story_bug_map = defaultdict(list)

    for bug in bug_tickets:
        linked  = str(bug.get('linked_issues') or bug.get('linked') or '')
        matched = False

        # Extract all Jira-style keys e.g. CT-101, PROJ-23
        keys_found = re.findall(r'[A-Z][A-Z0-9]+-[0-9]+', linked)

        for k in keys_found:
            if k in story_map:
                story_bug_map[k].append(bug)
                matched = True
                break  # map to first matching story

        if not matched:
            story_bug_map['__unlinked__'].append(bug)

    return dict(story_bug_map)
