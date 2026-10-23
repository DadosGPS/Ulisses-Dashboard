"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useLoadUser } from "@/lib/use-load-user";
import { createClient } from "@/lib/supabase/client";
import { cores, espaco } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";
import { estiloBotao, EstadoVazio } from "@/components/ui/base";
import type { KpiCarga } from "@/components/ui/KpiCargaCard";
import {
  CentroControlo,
  type Alerta,
  type ExposicaoSemana,
  type PlaneadoRealizado,
  type SquadStatus,
} from "@/components/dashboard/CentroControlo";
import { useTr, linguaDoCookie } from "@/lib/i18n/cliente";
import { Carregando } from "@/components/ui/Esqueleto";

export default function DashboardPage() {
  const tr = useTr();
  const router = useRouter();
  const user = useLoadUser();
  const [loading, setLoading] = useState(true);
  const [squadStatus, setSquadStatus] = useState<SquadStatus | null>(null);
  const [alerts, setAlerts] = useState<Alerta[]>([]);
  const [kpis, setKpis] = useState<KpiCarga[]>([]);
  const [sessaoRecente, setSessaoRecente] = useState<string | null>(null);
  const [baselineLabel, setBaselineLabel] = useState<string | null>(null);
  const [exposicao, setExposicao] = useState<ExposicaoSemana | null>(null);
  const [aCarregarExposicao, setACarregarExposicao] = useState(false);
  const [planeado, setPlaneado] = useState<PlaneadoRealizado | null>(null);

  // Troca só o painel de exposição para outro microciclo, sem recarregar o resto.
  async function escolherMicrociclo(mc: number) {
    if (!user.teamId) return;
    setACarregarExposicao(true);
    try {
      const { data: { session } } = await createClient().auth.getSession();
      if (!session) return;
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/teams/${user.teamId}/dashboard/exposicao-semana?microciclo=${mc}`,
        { headers: { Authorization: `Bearer ${session.access_token}`, "X-Lingua": linguaDoCookie() } },
      );
      if (res.ok) setExposicao(await res.json());
    } finally {
      setACarregarExposicao(false);
    }
  }

  useEffect(() => {
    if (user.isLoading) return;
    if (!user.teamId) {
      router.push("/login");
      return;
    }
    fetchDashboardData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user.teamId, user.isLoading]);

  async function fetchDashboardData() {
    try {
      setLoading(true);
      const teamId = user.teamId;

      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) {
        router.push("/login");
        return;
      }

      const apiBase = `${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}`;
      const opcoes = { headers: { Authorization: `Bearer ${token}`, "X-Lingua": linguaDoCookie() } };

      const [statusRes, alertsRes, cargaRes, exposicaoRes, planeadoRes] = await Promise.all([
        fetch(`${apiBase}/dashboard/squad-status`, opcoes),
        fetch(`${apiBase}/dashboard/attention-required`, opcoes),
        fetch(`${apiBase}/carga-externa`, opcoes),
        fetch(`${apiBase}/dashboard/exposicao-semana`, opcoes),
        fetch(`${apiBase}/dashboard/planeado-vs-realizado`, opcoes),
      ]);

      if (statusRes.ok) setSquadStatus(await statusRes.json());
      if (alertsRes.ok) setAlerts(await alertsRes.json());
      if (cargaRes.ok) {
        const carga = await cargaRes.json();
        setKpis(carga.kpis ?? []);
        setSessaoRecente(carga.sessao_recente ?? null);
        setBaselineLabel(carga.escopo?.baseline_label ?? null);
      }
      if (exposicaoRes.ok) setExposicao(await exposicaoRes.json());
      if (planeadoRes.ok) setPlaneado(await planeadoRes.json());
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
    } finally {
      setLoading(false);
    }
  }

  const semDados = !loading && !squadStatus && kpis.length === 0 && alerts.length === 0;
  const hoje = new Date().toLocaleDateString(tr.loc, { weekday: "long", day: "numeric", month: "long" });

  return (
    <div>
      <PageHeader
        titulo={tr("Centro de Controlo")}
        subtitulo={hoje.charAt(0).toUpperCase() + hoje.slice(1)}
        acoes={
          <>
            <button onClick={() => router.push("/mensagens")} style={estiloBotao.secundario}>{tr("Mensagens")}</button>
            <button onClick={() => router.push("/upload")} style={estiloBotao.primario}>{tr("Importar GPS")}</button>
          </>
        }
      />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, maxWidth: 1400 }}>
        {loading ? (
          <Carregando cartoes={3} linhas={8} padding={false} />
        ) : semDados ? (
          <EstadoVazio mensagem={tr("Ainda não há dados carregados para esta equipa. Importa os dados de GPS para veres o estado da equipa.")} acao={{ href: "/upload", label: tr("Importar GPS") }} />
        ) : (
          <CentroControlo
            squadStatus={squadStatus}
            alertas={alerts}
            kpis={kpis}
            sessaoRecente={sessaoRecente}
            baselineLabel={baselineLabel}
            exposicao={exposicao}
            planeado={planeado}
            aCarregarExposicao={aCarregarExposicao}
            onMicrociclo={escolherMicrociclo}
            navegar={(r) => router.push(r)}
          />
        )}
      </div>
    </div>
  );
}

