import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CONCILIA AI — Sistema Profissional de Conciliação Contábil Automática",
  description: "Auditoria matemática, conciliação contábil determinística e inteligência financeira.",
};

export default function RootLayout({
  children,
}: ReadencodedLayoutProps<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body className="bg-slate-50 text-slate-900 antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}

type ReadencodedLayoutProps<T> = T;
