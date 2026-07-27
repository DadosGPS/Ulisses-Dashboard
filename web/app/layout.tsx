import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";

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

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt" className={`${inter.variable} ${spaceGrotesk.variable}`}>
      <body>{children}</body>
    </html>
  );
}
