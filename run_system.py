"""
CONCILIA AI - Unified System Launcher
Starts both FastAPI backend (port 8000) and Next.js frontend (port 3000).
"""
import subprocess
import sys
import os
import time
import signal

def main():
    root_dir = os.path.abspath(os.path.dirname(__file__))
    backend_dir = os.path.join(root_dir, "backend")
    frontend_dir = os.path.join(root_dir, "frontend")

    print("=" * 70)
    print("  CONCILIA AI — SISTEMA PROFISSIONAL DE CONCILIAÇÃO CONTÁBIL")
    print("=" * 70)
    print(f"Diretório raiz: {root_dir}")

    # Seed database if needed
    if not os.path.exists(os.path.join(backend_dir, "data", "concilia_ai.db")):
        print("\n[1/3] Inicializando banco de dados e processando Razão.xls...")
        subprocess.run([sys.executable, "seed_database.py"], cwd=root_dir)

    print("\n[2/3] Iniciando Backend FastAPI (Porta 8000)...")
    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = backend_dir
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=backend_dir,
        env=backend_env
    )

    time.sleep(2)

    print("\n[3/3] Iniciando Frontend Next.js (Porta 3000)...")
    frontend_cmd = "npm run start" if os.path.exists(os.path.join(frontend_dir, ".next")) else "npm run dev"
    frontend_proc = subprocess.Popen(
        frontend_cmd,
        cwd=frontend_dir,
        shell=True
    )

    print("\n" + "=" * 70)
    print("  SISTEMA CONCILIA AI EM OPERAÇÃO!")
    print("  -> Frontend:     http://localhost:3000")
    print("  -> Backend API:  http://localhost:8000")
    print("  -> Swagger Docs: http://localhost:8000/docs")
    print("=" * 70)
    print("Pressione Ctrl+C para encerrar o sistema.\n")

    try:
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print("Backend encerrou inesperadamente.")
                break
            if frontend_proc.poll() is not None:
                print("Frontend encerrou inesperadamente.")
                break
    except KeyboardInterrupt:
        print("\nEncerrando CONCILIA AI...")
    finally:
        try:
            backend_proc.terminate()
            frontend_proc.terminate()
        except Exception:
            pass
        print("Sistema finalizado.")

if __name__ == "__main__":
    main()
