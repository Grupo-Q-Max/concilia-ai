"use client";

import React, { useState, useEffect } from "react";
import { 
  Sliders, 
  Save, 
  RotateCcw, 
  Sparkles, 
  CheckCircle2, 
  ShieldCheck, 
  Settings as SettingsIcon,
  RefreshCw,
  X
} from "lucide-react";
import { api } from "@/lib/api";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  activeJobId: string | null;
  onSettingsSaved: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  activeJobId,
  onSettingsSaved
}) => {
  const [settings, setSettings] = useState<any>({
    cent_tolerance: 0.05,
    supplier_similarity_threshold: 0.55,
    enable_exact_match: true,
    enable_cent_difference: true,
    enable_partial_payments: true,
    enable_grouped_payments: true,
    enable_reversals: true,
    enable_duplicate_detection: true,
    balance_convention: "AUTO",
    ai_provider: "HEURISTIC",
    ai_api_key: "",
    ai_model: "gpt-4o-mini",
    company_display_name: "CONCILIA AI Enterprise",
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      load();
    }
  }, [isOpen]);

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.getSettings();
      setSettings(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const handleSave = async (reprocessAfter: boolean = false) => {
    setSaving(true);
    setMsg(null);
    try {
      await api.updateSettings(settings);
      if (reprocessAfter && activeJobId) {
        setReprocessing(true);
        await api.reprocessJob(activeJobId);
      }
      setMsg(reprocessAfter 
        ? "Configurações salvas e conciliação reprocessada com sucesso!"
        : "Configurações salvas com sucesso!"
      );
      onSettingsSaved();
    } catch (err: any) {
      setMsg(`Erro ao salvar: ${err.message}`);
    } finally {
      setSaving(false);
      setReprocessing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 space-y-5 animate-in fade-in zoom-in-95 duration-150 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between pb-3 border-b border-slate-200">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
              <SettingsIcon className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Parâmetros & Configurações do Sistema</h3>
              <p className="text-xs text-slate-500">Ajuste regras contábeis, tolerâncias de centavos e inteligência artificial</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        {msg ? (
          <div className="p-3 rounded-lg bg-emerald-50 text-emerald-800 text-xs font-medium border border-emerald-200 flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-emerald-600" />
            <span>{msg}</span>
          </div>
        ) : null}

        <div className="space-y-5 text-xs">
          {/* Seção 1: Tolerâncias Financeiras */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
            <h4 className="font-bold text-slate-900 flex items-center space-x-2 text-sm">
              <Sliders className="w-4 h-4 text-blue-600" />
              <span>1. Tolerâncias & Precisão Contábil</span>
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Tolerância de Centavos (R$):
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="1.00"
                    value={settings.cent_tolerance}
                    onChange={(e) => setSettings({ ...settings, cent_tolerance: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-1.5 rounded-lg border border-slate-300 font-mono text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  />
                  <span className="text-[11px] text-slate-400 whitespace-nowrap">Ex: 0.05</span>
                </div>
                <p className="text-[10px] text-slate-400 mt-1">Divergências até esse valor são associadas como resíduo.</p>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Similaridade Mínima Fornecedor (%):
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="range"
                    min="0.4"
                    max="0.9"
                    step="0.05"
                    value={settings.supplier_similarity_threshold}
                    onChange={(e) => setSettings({ ...settings, supplier_similarity_threshold: parseFloat(e.target.value) })}
                    className="w-full"
                  />
                  <span className="font-mono font-bold text-slate-800 w-12 text-right">
                    {Math.round(settings.supplier_similarity_threshold * 100)}%
                  </span>
                </div>
                <p className="text-[10px] text-slate-400 mt-1">Nível de rigor para aceitar variações no nome do fornecedor.</p>
              </div>
            </div>
          </div>

          {/* Seção 2: Módulos de Conciliação Ativos */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
            <h4 className="font-bold text-slate-900 flex items-center space-x-2 text-sm">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>2. Regras de Conciliação Habilitadas</span>
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <label className="flex items-center space-x-2 cursor-pointer p-2 rounded-lg bg-white border border-slate-200 hover:border-slate-300">
                <input
                  type="checkbox"
                  checked={settings.enable_exact_match}
                  onChange={(e) => setSettings({ ...settings, enable_exact_match: e.target.checked })}
                  className="rounded text-blue-600 focus:ring-blue-500"
                />
                <span className="font-medium text-slate-800">Quitação Exata 1-para-1</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer p-2 rounded-lg bg-white border border-slate-200 hover:border-slate-300">
                <input
                  type="checkbox"
                  checked={settings.enable_cent_difference}
                  onChange={(e) => setSettings({ ...settings, enable_cent_difference: e.target.checked })}
                  className="rounded text-blue-600 focus:ring-blue-500"
                />
                <span className="font-medium text-slate-800">Tolerância de Centavos</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer p-2 rounded-lg bg-white border border-slate-200 hover:border-slate-300">
                <input
                  type="checkbox"
                  checked={settings.enable_partial_payments}
                  onChange={(e) => setSettings({ ...settings, enable_partial_payments: e.target.checked })}
                  className="rounded text-blue-600 focus:ring-blue-500"
                />
                <span className="font-medium text-slate-800">Amortizações Parciais</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer p-2 rounded-lg bg-white border border-slate-200 hover:border-slate-300">
                <input
                  type="checkbox"
                  checked={settings.enable_grouped_payments}
                  onChange={(e) => setSettings({ ...settings, enable_grouped_payments: e.target.checked })}
                  className="rounded text-blue-600 focus:ring-blue-500"
                />
                <span className="font-medium text-slate-800">Baixas em Lote / Agrupadas</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer p-2 rounded-lg bg-white border border-slate-200 hover:border-slate-300">
                <input
                  type="checkbox"
                  checked={settings.enable_reversals}
                  onChange={(e) => setSettings({ ...settings, enable_reversals: e.target.checked })}
                  className="rounded text-blue-600 focus:ring-blue-500"
                />
                <span className="font-medium text-slate-800">Compensação de Estornos</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer p-2 rounded-lg bg-white border border-slate-200 hover:border-slate-300">
                <input
                  type="checkbox"
                  checked={settings.enable_duplicate_detection}
                  onChange={(e) => setSettings({ ...settings, enable_duplicate_detection: e.target.checked })}
                  className="rounded text-blue-600 focus:ring-blue-500"
                />
                <span className="font-medium text-slate-800">Detecção de Duplicidades</span>
              </label>
            </div>
          </div>

          {/* Seção 3: Inteligência Artificial */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
            <h4 className="font-bold text-slate-900 flex items-center space-x-2 text-sm">
              <Sparkles className="w-4 h-4 text-amber-500" />
              <span>3. Motor de Inteligência Artificial</span>
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Provedor de IA:
                </label>
                <select
                  value={settings.ai_provider}
                  onChange={(e) => setSettings({ ...settings, ai_provider: e.target.value })}
                  className="w-full px-3 py-1.5 rounded-lg border border-slate-300 bg-white font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                >
                  <option value="HEURISTIC">Heurística Local (Sem custos / Autônomo)</option>
                  <option value="OPENAI">OpenAI API (Compatível GPT-4o)</option>
                  <option value="GEMINI">Google Gemini API</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Chave de API (Opcional):
                </label>
                <input
                  type="password"
                  placeholder="sk-... ou chave do provedor"
                  value={settings.ai_api_key || ""}
                  onChange={(e) => setSettings({ ...settings, ai_api_key: e.target.value })}
                  className="w-full px-3 py-1.5 rounded-lg border border-slate-300 font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-slate-200">
          <button
            onClick={() => setSettings({
              cent_tolerance: 0.05,
              supplier_similarity_threshold: 0.55,
              enable_exact_match: true,
              enable_cent_difference: true,
              enable_partial_payments: true,
              enable_grouped_payments: true,
              enable_reversals: true,
              enable_duplicate_detection: true,
              balance_convention: "AUTO",
              ai_provider: "HEURISTIC",
              ai_api_key: "",
              ai_model: "gpt-4o-mini",
            })}
            className="flex items-center space-x-1.5 text-slate-500 hover:text-slate-800 text-xs font-semibold"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Restaurar Padrões</span>
          </button>

          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800"
            >
              Fechar
            </button>
            <button
              disabled={saving || reprocessing}
              onClick={() => handleSave(false)}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-semibold shadow transition disabled:opacity-50"
            >
              {saving ? "Salvando..." : "Salvar Configurações"}
            </button>
            {activeJobId ? (
              <button
                disabled={saving || reprocessing}
                onClick={() => handleSave(true)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow transition flex items-center space-x-1.5 disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${reprocessing ? "animate-spin" : ""}`} />
                <span>Salvar & Reprocessar Razão</span>
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
};
