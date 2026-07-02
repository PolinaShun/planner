import subprocess, json

with open("C:\\Users\\Honor\\planner\\gh_token.txt") as f:
    token = f.read().strip()

auth_header = "Authorization: Bearer " + token
url = "https://api.github.com/repos/PolinaShun/planner/actions/runs?per_page=5"

r = subprocess.run(["curl", "-s", "-H", auth_header, url], capture_output=True, text=True)
data = json.loads(r.stdout)

for run in data.get("workflow_runs", []):
    print(f"Run #{run['run_number']}: {run['status']}/{run['conclusion']} - {run['head_sha'][:7]} {run['display_title']}")
