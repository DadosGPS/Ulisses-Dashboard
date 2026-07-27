import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LoadMonitorSystem",
  description: "Monitorização de carga desportiva",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt">
      <body>{children}</body>
    </html>
  );
}
