#!/usr/bin/env python3
import subprocess, json
with open("C:\\Users\\Honor\\planner\\gh_token.txt") as f:
    token = f.read().strip()
r = subprocess.run(['curl', '-s', '-H', f'Authorization: Bearer *** 'https://api.github.com/repos/PolinaShun/planner/actions/runs?per_page=1'], capture_output=True, text=True)
data = json.loads(r.stdout)
if 'workflow_runs' in data:
    run = data['workflow_runs'][0]
    print(f"Run #{run['run_number']}: {run['status']} / {run['conclusion']}")
    print(f"Commit: {run['head_sha'][:7]} - {run['display_title']}")
else:
    print(json.dumps(data, indent=2)[:300])