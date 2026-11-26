"use client";
import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
export function Appearance() {
  const [dark, setDark] = useState(false);
  useEffect(() => { try { setDark(localStorage.getItem("concilia-theme") === "dark"); } catch {} }, []);
  useEffect(() => { document.documentElement.dataset.theme = dark ? "dark" : "light"; }, [dark]);
  return <button type="button" className="appearance-toggle" title={dark ? "Tema claro" : "Tema escuro"} aria-label={dark ? "Ativar tema claro" : "Ativar tema escuro"} onClick={() => { const next = !dark; setDark(next); try { localStorage.setItem("concilia-theme", next ? "dark" : "light"); } catch {} }}>{dark ? <Sun size={17}/> : <Moon size={17}/>}</button>;
}
