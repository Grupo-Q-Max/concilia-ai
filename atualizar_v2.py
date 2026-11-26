from pathlib import Path
from datetime import datetime
import shutil
import re

root = Path.cwd()
backup = root / ("backup_v2_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
backup.mkdir()

def read(name):
    return (root / name).read_text(encoding="utf-8-sig")

def save(name, content):
    path = root / name
    dest = backup / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    path.write_text(content, encoding="utf-8")

def replace(text, old, new):
    if old not in text:
        raise RuntimeError("Trecho nao encontrado: " + old[:100])
    return text.replace(old, new, 1)

routes_name = "backend/app/api/routes.py"
routes = read(routes_name)

if "def delete_history_v2(" in routes:
    raise RuntimeError("Atualizacao ja aplicada.")

routes += '''

# CONCILIA AI V2 - History management
@router.delete("/history")
def delete_history_v2():
    conn = get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM jobs")
        return {"success": True}
    finally:
        conn.close()


@router.delete("/history/{job_id}")
def delete_history_job_v2(job_id: str):
    conn = get_connection()
    try:
        with conn:
            result = conn.execute(
                "DELETE FROM jobs WHERE id = ?", (job_id,)
            )
            if result.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Documento nao encontrado."
                )
        return {"success": True}
    finally:
        conn.close()
'''

api_name = "frontend/src/lib/api.ts"
api = read(api_name)

api, n = re.subn(
    r"const API_BASE\s*=.*?;",
    '''const API_BASE = typeof window !== "undefined" && window.location.port === "3000"
  ? (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001/api")
  : "/api";''',
    api,
    count=1
)
if n != 1:
    raise RuntimeError("API_BASE nao encontrada.")

api += '''

export async function deleteHistory(jobId?: string) {
  const url = jobId
    ? `${API_BASE}/history/${encodeURIComponent(jobId)}`
    : `${API_BASE}/history`;
  const response = await fetch(url, { method: "DELETE" });
  if (!response.ok) {
    throw new Error("Nao foi possivel excluir o documento.");
  }
  return response.json();
}
'''

page_name = "frontend/src/app/page.tsx"
page = read(page_name)

page = replace(
    page,
    'import { api } from "@/lib/api";',
    'import { api, deleteHistory } from "@/lib/api";'
)

page = replace(
    page,
    '  const counts = {',
    '''
  const [deleting, setDeleting] = useState(false);

  const removeHistory = async (id?: string) => {
    const message = id
      ? "Excluir este documento e sua conciliacao?"
      : "Excluir TODOS os documentos do historico?";
    if (!window.confirm(message)) return;

    setDeleting(true);
    try {
      await deleteHistory(id);
      window.location.reload();
    } catch (err: any) {
      window.alert(err.message);
    } finally {
      setDeleting(false);
    }
  };

  const counts = {'''
)

page = replace(
    page,
    'job={jobSummary?.job}',
    'job={jobSummary?.job?.id === activeJobId ? jobSummary.job : undefined}'
)

anchor = '      <div className="flex-1 flex max-w-7xl w-full mx-auto">'

page = replace(page, anchor, '''
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex flex-wrap items-center gap-3">
        <label htmlFor="document-selector" className="text-xs font-bold text-slate-700">
          Documento selecionado
        </label>
        <select
          id="document-selector"
          value={activeJobId || ""}
          disabled={loading || deleting || jobs.length === 0}
          onChange={(e) => {
            setJobSummary(null);
            setLoading(true);
            setActiveJobId(e.target.value);
            setCurrentTab("dashboard");
          }}
          className="flex-1 min-w-0 max-w-2xl border border-slate-300 rounded-lg px-3 py-2 text-sm bg-slate-50"
        >
          <option value="" disabled>Nenhum documento selecionado</option>
          {jobs.map((j) => (
            <option key={j.id} value={j.id}>
              {j.filename} - {j.company_name} - {j.period} - {new Date(j.created_at).toLocaleString("pt-BR")}
            </option>
          ))}
        </select>
        <span className="text-xs text-slate-500">
          {jobs.length} documento(s)
        </span>
        <button
          disabled={loading || deleting || !activeJobId}
          onClick={() => removeHistory(activeJobId || undefined)}
          className="border border-red-200 text-red-700 rounded-lg px-3 py-2 text-xs font-semibold disabled:opacity-40"
        >
          Excluir selecionado
        </button>
        <button
          disabled={loading || deleting || jobs.length === 0}
          onClick={() => removeHistory()}
          className="bg-red-600 hover:bg-red-700 text-white rounded-lg px-3 py-2 text-xs font-semibold disabled:opacity-40"
        >
          Limpar historico
        </button>
      </div>

''' + anchor)

page = replace(
    page,
    '                            {j.status}',
    '                            {activeJobId === j.id ? "Selecionado" : j.status}'
)

page = replace(
    page,
    '                          </span>\n                        </div>\n                      </div>\n                    ))}',
    '''                          </span>
                          <button
                            disabled={loading || deleting}
                            onClick={(e) => {
                              e.stopPropagation();
                              removeHistory(j.id);
                            }}
                            className="block ml-auto mt-2 text-xs font-semibold text-red-600 hover:underline"
                          >
                            Excluir documento
                          </button>
                        </div>
                      </div>
                    ))}'''
)

launcher_name = "launcher.py"
launcher = read(launcher_name)

launcher = re.sub(
    r"    # Seed demo file if available.*?(?=    settings = load_settings\(\))",
    "    # Automatic demo import disabled in V2\n\n",
    launcher,
    flags=re.S
)

save(routes_name, routes)
save(api_name, api)
save(page_name, page)
save(launcher_name, launcher)

print("ATUALIZACAO V2 APLICADA!")
print("Backup:", backup)
