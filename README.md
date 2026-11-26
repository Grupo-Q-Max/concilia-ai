# CONCILIA AI — Sistema Profissional de Conciliação Contábil Automática

> **CONCILIA AI** é uma plataforma corporativa completa desenvolvida para automatizar, auditar e conciliar razões contábeis com rigor matemático, rastreabilidade ponta a ponta e inteligência artificial para resolução de fornecedores e documentos.

---

## 1. Visão Geral e Arquitetura

O sistema foi arquitetado com separação clara de responsabilidades, garantindo performance, segurança e precisão contábil com **Decimal determinístico**:

* **Frontend:** Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Lucide Icons. Interface moderna, executiva e responsiva em tons de azul-marinho (`#0b132b`), branco, cinza, verde (`#10b981`), amarelo (`#f59e0b`) e vermelho (`#ef4444`).
* **Backend:** Python 3, FastAPI, Uvicorn, Pydantic v2.
* **Banco de Dados:** SQLite com precisão monetária (Decimal) e suporte a histórico e rastreabilidade total.
* **Motor Contábil & Parser:** Pandas, OpenPyXL, xlrd (capaz de ler `.xls`, `.xlsx` e `.csv` de múltiplos softwares contábeis, descobrindo cabeçalhos dinamicamente).
* **Exportação Profissional:** OpenPyXL (Planilha Excel com 8 abas analíticas estilizadas) e ReportLab (Laudo Executivo em PDF).
* **Auditoria Matemática:** Validação obrigatória da equação contábil de passivo e reconciliação com o saldo informado no arquivo.

---

## 2. Resultados da Demonstração Real: `Razão.xls`

O arquivo de teste `Razão.xls` foi processado integralmente pelo motor. Abaixo está o relatório consolidado da conciliação:

| Indicador Contábil | Valor Auditado | Observações |
| :--- | :--- | :--- |
| **Empresa Auditada** | `ASSOCIAÇÃO DA INSTITUIDORA E DOS LOCATÁRIOS DO PARQUE LOGÍSTICO GUARULHOS III` | Detectada no cabeçalho |
| **CNPJ** | `66.404.820/0001-57` | Extraído via regex |
| **Período** | `01/01/2026 - 30/09/2026` | 9 meses de movimentação |
| **Conta Contábil** | `2.1.30.100.000` | Passivo / Fornecedores |
| **Total Faturado (Créditos)** | **R$ 1.452.557,16** | 94 notas de entrada / provisões |
| **Total Baixado (Débitos)** | **R$ 1.323.356,46** | 88 baixas e pagamentos bancários |
| **Variação Líquida do Período** | **R$ 129.200,70** | Posição líquida credora |
| **Saldo Informado no Razão** | **R$ 15.583,16** | **Saldo da última movimentação (2026-09-30)** |
| **Total Conciliado em Títulos** | **R$ 1.323.356,46** | 86 pares exatos 1-para-1 |
| **Divergências de Centavos** | **R$ 0,02** | 2 notas com R$ 0,01 de resíduo |
| **Posição Final em Aberto** | **R$ 129.200,68** | 6 notas fiscais a pagar |

### Origem Matemática do Saldo de R$ 15.583,16
Conforme investigado minuciosamente na estrutura analítica do relatório:
1. No software contábil de origem (**Q-MAX CONTÁBIL LTDA**), a coluna **"Saldo"** funciona como um **acumulador analítico mensal**, sendo reiniciada a zero no primeiro dia útil de cada mês.
2. Na competência de Setembro/2026:
   $$\text{Débitos de Setembro (R\$ 554.569,38)} - \text{Créditos de Setembro (R\$ 538.986,22)} = \mathbf{R\$\ 15.583,16}$$
3. O saldo informado na última linha do razão contábil (**R$ 15.583,16**) corresponde exatamente a essa movimentação líquida da competência final.
4. Por sua vez, a posição de títulos a pagar no fechamento contábil é comprovada sem nenhum centavo de erro:
   $$\text{Títulos em Aberto (R\$ 129.200,68)} + \text{Divergência Centavos (R\$ 0,02)} = \text{Movimento Líquido do Período (R\$ 129.200,70)}$$

---

## 3. Títulos em Aberto e Divergências Identificadas

### Notas Fiscais em Aberto (Total: R$ 129.200,68)
1. **NF 132753** — CUSHMAN & WAKEFIELD: R$ 8.899,22 (10/09/2026)
2. **NF 132763** — CUSHMAN & WAKEFIELD: R$ 40.598,38 (10/09/2026)
3. **NF 132891** — CUSHMAN & WAKEFIELD: R$ 69.449,00 (15/09/2026)
4. **NF 20833** — UPS TECNOLOGIA LTDA: R$ 429,08 (24/09/2026)
5. **NF 20834** — UPS TECNOLOGIA LTDA: R$ 410,00 (24/09/2026)
6. **NF 25769** — APOIO TINTAS CENTER MATERIAIS: R$ 9.415,00 (12/06/2026)

### Divergências de Centavos Identificadas (Total: R$ 0,02)
1. **NF 54994** — Provisão R$ 6.492,96 vs Pagamento R$ 6.492,95 $\rightarrow$ Diferença residual de **+R$ 0,01**
2. **NF 56421** — Provisão R$ 10.018,73 vs Pagamento R$ 10.018,72 $\rightarrow$ Diferença residual de **+R$ 0,01**

---

## 4. Estrutura do Projeto

```
concilia-ai/
├── Razão.xls                  # Arquivo contábil de referência
├── seed_database.py           # Script de carga inicial do Razão.xls no banco
├── run_system.py              # Inicializador unificado (Backend + Frontend)
├── start.bat                  # Atalho Windows para execução em 1 clique
├── backend/
│   ├── app/
│   │   ├── main.py            # Entrypoint FastAPI e CORS
│   │   ├── config.py          # Configurações de diretórios e tolerâncias
│   │   ├── database.py        # SQLite com rastreabilidade
│   │   ├── schemas.py         # Modelos Pydantic v2
│   │   ├── api/
│   │   │   └── routes.py      # Endpoints REST (upload, conciliação, exports)
│   │   └── engine/
│   │       ├── parser.py      # Importador inteligente de múltiplos layouts
│   │       ├── extractor.py   # Extração regex/heurística de NFs e Fornecedores
│   │       ├── ai_matcher.py  # Similaridade fuzzy de nomes corporativos
│   │       ├── reconciler.py  # Motor determinístico com Decimal (multi-pass)
│   │       ├── balance_validator.py # Auditoria matemática do razão
│   │       └── exporter.py    # Gerador de Excel 8 abas e PDF ReportLab
│   ├── tests/
│   │   └── test_reconciler_edge_cases.py # Testes de parciais, agrupados, centavos, etc.
│   └── requirements.txt       # Dependências Python
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── tailwind.config.ts
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   └── page.tsx       # Interface SPA com navegação por abas
        ├── components/
        │   ├── Header.tsx     # Cabeçalho corporativo com exportações
        │   ├── Sidebar.tsx    # Menu com badges dinâmicos de contagem
        │   ├── Dashboard.tsx  # Gráficos, KPIs e memórias
        │   ├── ReconciledTable.tsx    # Tabela de conciliadas com busca
        │   ├── OpenInvoicesTable.tsx  # Títulos em aberto a pagar
        │   ├── DivergencesTable.tsx   # Divergências de centavos e desvios
        │   ├── ManualMatchModal.tsx   # Conciliação assistida interativa
        │   ├── SupplierSummaryTable.tsx # Posição financeira por parceiro
        │   ├── MathAuditModal.tsx     # Modal de memória de cálculo
        │   └── UploadModal.tsx        # Drag-and-drop de novos arquivos
        └── lib/
            └── api.ts         # Cliente HTTP TypeScript
```

---

## 5. Como Executar o Sistema

### Opção 1: Executável Standalone Windows (Recomendado — Zero Instalação!)
Basta dar um duplo clique diretamente no arquivo executável:
```cmd
ConciliaAI.exe
```
*(Também localizado em `dist/ConciliaAI.exe`)*

**Vantagens do Executável Standalone:**
* **Zero Dependências:** Não precisa ter Python, Node.js ou npm instalados no computador.
* **Tudo Embutido:** O backend FastAPI, banco SQLite, motor contábil e a interface Next.js já estão empacotados dentro do arquivo `.exe`.
* **Abertura Automática:** Ao ser iniciado, abre automaticamente seu navegador padrão na tela do sistema (`http://localhost:8000`).
* **Portabilidade:** Você pode copiar este único arquivo `ConciliaAI.exe` e levar para qualquer colega, cliente ou máquina Windows!

### Opção 2: Inicialização via Script Batch
Dê um duplo clique no arquivo:
```cmd
start.bat
```
Ou no terminal PowerShell / CMD:
```cmd
python run_system.py
```
O script iniciará automaticamente:
* O Backend FastAPI em `http://localhost:8000`
* O Frontend Next.js em `http://localhost:3000`

### Opção 2: Inicialização Manual dos Serviços

**1. Backend (FastAPI):**
```bash
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```
Acesse a documentação interativa da API (Swagger): `http://localhost:8000/docs`

**2. Frontend (Next.js):**
```bash
cd frontend
npm run start
# ou para desenvolvimento com hot-reload:
npm run dev
```
Acesse o aplicativo no navegador: `http://localhost:3000`

---

## 6. Testes Automatizados Executados

Execute a suíte de testes com:
```bash
python backend/tests/test_reconciler_edge_cases.py
```
Testes integrados cobrem:
* **Conciliação exata 1-para-1:** Validação por NF e fornecedor.
* **Diferenças de centavos:** Casos de tolerância de arredondamento ($\le$ R$ 0,05).
* **Pagamentos parciais:** Amortização progressiva com guarda do saldo restante a pagar.
* **Pagamentos agrupados:** Múltiplas notas quitadas em lote pelo mesmo pagamento.
* **Estornos e cancelamentos:** Compensação mútua imediata sem duplicar baixas.
* **Auditoria de saldos:** Validação da convenção de sinais e equação do razão contábil.
