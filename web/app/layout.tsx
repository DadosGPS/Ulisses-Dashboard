import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";
import { scriptTemaInicial } from "@/lib/tema-config";
import { SincronizarTema } from "@/lib/tema";
import { LinguaProvider } from "@/lib/i18n/cliente";
import { obterLingua } from "@/lib/i18n/servidor";

// Space Grotesk para títulos/números de destaque, Inter para o resto —
// mesma combinação que dashboard.py já usava via CSS injetado no Streamlit,
// agora carregada de forma própria e fiável (next/font, sem @import externo).
const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  title: "LoadMonitorSystem",
  description: "Monitorização de carga desportiva",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const lingua = await obterLingua();
  return (
    <html lang={lingua} className={`${inter.variable} ${spaceGrotesk.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: scriptTemaInicial }} />
      </head>
      <body>
        <SincronizarTema />
        <LinguaProvider lingua={lingua}>{children}</LinguaProvider>
      </body>
    </html>
  );
}
