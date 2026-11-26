"""
CONCILIA AI — Desktop Application Launcher
Unified entrypoint compiled into standalone Windows Executable (ConciliaAI.exe).
Starts FastAPI backend + embedded Next.js frontend and opens the browser automatically.
"""
import os
import sys
import time
import socket
import webbrowser
import threading
from pathlib import Path

# Adjust paths for PyInstaller bundle or local script
if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys._MEIPASS)
    EXE_DIR = Path(sys.executable).parent
    os.chdir(str(EXE_DIR))
else:
    APP_DIR = Path(__file__).resolve().parent
    EXE_DIR = APP_DIR

# Ensure backend directory is in sys.path
backend_path = str(APP_DIR / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import uvicorn
from app.main import app
from app.database import init_db
from app.config import load_settings

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def find_available_port(start_port: int = 8000) -> int:
    port = start_port
    while is_port_in_use(port) and port < 8100:
        port += 1
    return port

def open_browser_delayed(url: str, delay: float = 1.2):
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Não foi possível abrir o navegador automaticamente: {e}")

def main():
    print("=" * 70)
    print("      CONCILIA AI — SISTEMA PROFISSIONAL DE CONCILIAÇÃO CONTÁBIL")
    print("=" * 70)
    print("  Status: Inicializando banco de dados e motor analítico...")

    try:
        init_db()
    except Exception as e:
        print(f"  Aviso na inicialização do banco: {e}")

    # Automatic demo import disabled in V2

    settings = load_settings()
    port = find_available_port(8000)
    url = f"http://127.0.0.1:{port}"

    print(f"  Interface Web:    {url}")
    print(f"  Documentação API: {url}/docs")
    print("=" * 70)
    print("  O aplicativo está pronto! Abrindo seu navegador...")
    print("  (Para encerrar, feche esta janela ou pressione Ctrl+C)")
    print("=" * 70)

    # Launch browser in background thread
    if settings.get("auto_open_browser", True):
        threading.Thread(target=open_browser_delayed, args=(url, 1.2), daemon=True).start()

    # Run Uvicorn server
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        input("Pressione Enter para sair")
        raise
