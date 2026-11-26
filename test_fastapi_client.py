import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)

# 1. Health
res = client.get("/api/health")
print("Health:", res.status_code, res.json())

# 2. Jobs
res = client.get("/api/jobs")
print("Jobs:", res.status_code, len(res.json()))
assert len(res.json()) > 0
job_id = res.json()[0]["id"]

# 3. Summary
res = client.get(f"/api/reconciliation/{job_id}/summary")
print("Summary status:", res.status_code)
data = res.json()
print("Company:", data["job"]["company_name"])
print("Reported Final Balance:", data["job"]["final_reported_balance"])
print("Math Status:", data["job"]["math_validation_status"])

# 4. Reconciled
res = client.get(f"/api/reconciliation/{job_id}/reconciled")
print("Reconciled status:", res.status_code, "Count:", len(res.json()))

# 5. Open
res = client.get(f"/api/reconciliation/{job_id}/open")
print("Open status:", res.status_code, "Count:", len(res.json()))

# 6. Divergences
res = client.get(f"/api/reconciliation/{job_id}/divergences")
print("Divergences status:", res.status_code, "Pairs:", len(res.json()["divergent_pairs"]))

# 7. Supplier Summary
res = client.get(f"/api/reconciliation/{job_id}/supplier-summary")
print("Supplier summary status:", res.status_code, "Count:", len(res.json()))

print("\nALL IN-PROCESS FASTAPI ENDPOINTS RETURNED 200 OK!")
