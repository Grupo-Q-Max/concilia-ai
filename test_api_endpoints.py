"""
Integration test: starts backend, probes all endpoints, verifies responses.
"""
import subprocess
import time
import urllib.request
import json
import sys
import os

backend_dir = os.path.abspath("backend")
env = os.environ.copy()
env["PYTHONPATH"] = backend_dir

print("Starting backend subprocess...")
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8888"],
    cwd=backend_dir,
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

try:
    time.sleep(3)
    
    # 1. Probe health
    url_health = "http://127.0.0.1:8888/api/health"
    with urllib.request.urlopen(url_health, timeout=5) as res:
        health_data = json.loads(res.read().decode())
        print("Health status:", health_data)
        assert health_data["status"] == "ok"

    # 2. Probe jobs
    url_jobs = "http://127.0.0.1:8888/api/jobs"
    with urllib.request.urlopen(url_jobs, timeout=5) as res:
        jobs = json.loads(res.read().decode())
        print(f"Jobs count: {len(jobs)}")
        assert len(jobs) > 0
        job_id = jobs[0]["id"]

    # 3. Probe summary
    url_sum = f"http://127.0.0.1:8888/api/reconciliation/{job_id}/summary"
    with urllib.request.urlopen(url_sum, timeout=5) as res:
        sum_data = json.loads(res.read().decode())
        print(f"Summary loaded: {sum_data['job']['company_name']}")
        print(f"Reported final balance: R$ {sum_data['job']['final_reported_balance']}")
        print(f"Math validation status: {sum_data['job']['math_validation_status']}")
        assert sum_data["job"]["final_reported_balance"] == "15583.16"

    # 4. Probe reconciled
    url_rec = f"http://127.0.0.1:8888/api/reconciliation/{job_id}/reconciled"
    with urllib.request.urlopen(url_rec, timeout=5) as res:
        rec_data = json.loads(res.read().decode())
        print(f"Reconciled pairs count: {len(rec_data)}")
        assert len(rec_data) >= 86

    # 5. Probe open
    url_open = f"http://127.0.0.1:8888/api/reconciliation/{job_id}/open"
    with urllib.request.urlopen(url_open, timeout=5) as res:
        open_data = json.loads(res.read().decode())
        print(f"Open invoices count: {len(open_data)}")
        assert len(open_data) == 6

    # 6. Probe divergences
    url_div = f"http://127.0.0.1:8888/api/reconciliation/{job_id}/divergences"
    with urllib.request.urlopen(url_div, timeout=5) as res:
        div_data = json.loads(res.read().decode())
        print(f"Divergent pairs (cent diff): {len(div_data['divergent_pairs'])}")
        assert len(div_data["divergent_pairs"]) == 2

    # 7. Probe supplier summary
    url_sup = f"http://127.0.0.1:8888/api/reconciliation/{job_id}/supplier-summary"
    with urllib.request.urlopen(url_sup, timeout=5) as res:
        sup_data = json.loads(res.read().decode())
        print(f"Suppliers count: {len(sup_data)}")
        assert len(sup_data) > 0

    print("\nALL API ENDPOINTS VALIDATED SUCCESSFULLY WITH 100% PASS RATE!")

finally:
    proc.terminate()
    proc.wait()
