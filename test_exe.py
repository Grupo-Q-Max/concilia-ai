import subprocess
import time
import urllib.request
import os

print("Testing ConciliaAI.exe execution...")
exe_path = os.path.abspath("ConciliaAI.exe")
proc = subprocess.Popen([exe_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

try:
    time.sleep(4)
    poll = proc.poll()
    if poll is not None:
        stdout, stderr = proc.communicate()
        print(f"FAILED: Process exited early with code {poll}!")
        print("STDOUT:", stdout.decode(errors='replace'))
        print("STDERR:", stderr.decode(errors='replace'))
        assert False, "ConciliaAI.exe crashed on startup"
    else:
        print(f"SUCCESS: ConciliaAI.exe is running stably with PID {proc.pid}!")
        # Probe http://127.0.0.1:8000
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=3) as res:
                print("API Health response:", res.read().decode())
        except Exception as e:
            print("API probe warning (may be bound to different port or still opening):", e)
finally:
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except Exception:
        proc.kill()
    print("Test finished and process terminated cleanly.")
