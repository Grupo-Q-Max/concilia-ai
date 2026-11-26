import os
import shutil
import zipfile

pkg_dir = "Concilia AI"
if os.path.exists(pkg_dir):
    shutil.rmtree(pkg_dir)

os.makedirs(pkg_dir, exist_ok=True)

# Copy exe
shutil.copy("ConciliaAI.exe", os.path.join(pkg_dir, "ConciliaAI.exe"))

# Copy sample excel
sample_src = "Razão.xls" if os.path.exists("Razão.xls") else "Razão (1).xls"
if os.path.exists(sample_src):
    shutil.copy(sample_src, os.path.join(pkg_dir, "Razão (Exemplo de Teste).xls"))

# Create Como Usar
readme_content = """======================================================================
      CONCILIA AI — SISTEMA PROFISSIONAL DE CONCILIAÇÃO CONTÁBIL
======================================================================

COMO USAR:

1. Dê um duplo clique no arquivo 'ConciliaAI.exe'.
2. O sistema abrirá automaticamente no seu navegador de internet.
3. Clique no botão azul 'Importar Razão' para selecionar sua planilha 
   de razão contábil (ou use a planilha 'Razão (Exemplo de Teste).xls' inclusa).
4. O sistema faz a conciliação automática, audita o saldo e gera o
   Contas a Pagar em aberto.
5. Você pode exportar a qualquer momento a planilha em Excel (8 abas)
   ou o Laudo Executivo em PDF pelos botões no topo.

REQUISITOS:
- Windows 10 ou 11 (64 bits).
- Não precisa de Python, não precisa de internet e não precisa instalar nada!
======================================================================
"""

with open(os.path.join(pkg_dir, "COMO_USAR.txt"), "w", encoding="utf-8") as f:
    f.write(readme_content)

# Create zip file
zip_name = "Concilia_AI.zip"
if os.path.exists(zip_name):
    os.remove(zip_name)

print("Creating Concilia_AI.zip...")
with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, _, files in os.walk(pkg_dir):
        for file in files:
            full_path = os.path.join(root, file)
            arcname = os.path.relpath(full_path, start=".")
            zf.write(full_path, arcname)

print("Concilia_AI.zip created successfully!")
print("Size:", os.path.getsize(zip_name), "bytes")
