"use client";

// Body map esquemático (frente + costas) com zonas coloridas pela frequência
// de lesão. Cada zona pode ter uma ou duas elipses (pares esquerda/direita).

export interface ZonaDef {
  chave: string;
  label: string;
}

// Zonas disponíveis (para o formulário e o mapa).
export const ZONAS: ZonaDef[] = [
  { chave: "cabeca", label: "Cabeça" },
  { chave: "pescoco", label: "Pescoço" },
  { chave: "ombro", label: "Ombro" },
  { chave: "braco", label: "Braço" },
  { chave: "peito", label: "Peito" },
  { chave: "abdomen", label: "Abdómen" },
  { chave: "lombar", label: "Lombar" },
  { chave: "anca_virilha", label: "Anca / Virilha" },
  { chave: "coxa_ant", label: "Coxa anterior (quadríceps)" },
  { chave: "coxa_post", label: "Coxa posterior (isquiotibiais)" },
  { chave: "joelho", label: "Joelho" },
  { chave: "canela", label: "Canela" },
  { chave: "gemeos", label: "Gémeos" },
  { chave: "tornozelo", label: "Tornozelo" },
  { chave: "pe", label: "Pé" },
];

type El = [number, number, number, number]; // cx, cy, rx, ry
const FRENTE: Record<string, El[]> = {
  cabeca: [[60, 22, 13, 15]],
  pescoco: [[60, 40, 6, 5]],
  ombro: [[33, 56, 10, 8], [87, 56, 10, 8]],
  braco: [[20, 92, 7, 28], [100, 92, 7, 28]],
  peito: [[60, 70, 20, 13]],
  abdomen: [[60, 100, 18, 16]],
  anca_virilha: [[60, 130, 16, 10]],
  coxa_ant: [[48, 166, 11, 26], [72, 166, 11, 26]],
  joelho: [[48, 202, 9, 9], [72, 202, 9, 9]],
  canela: [[48, 240, 8, 22], [72, 240, 8, 22]],
  tornozelo: [[48, 280, 7, 6], [72, 280, 7, 6]],
  pe: [[47, 300, 9, 7], [73, 300, 9, 7]],
};
const COSTAS: Record<string, El[]> = {
  cabeca: [[60, 22, 13, 15]],
  pescoco: [[60, 40, 6, 5]],
  ombro: [[33, 56, 10, 8], [87, 56, 10, 8]],
  braco: [[20, 92, 7, 28], [100, 92, 7, 28]],
  lombar: [[60, 108, 18, 14]],
  anca_virilha: [[60, 132, 16, 9]],
  coxa_post: [[48, 166, 11, 26], [72, 166, 11, 26]],
  joelho: [[48, 202, 9, 9], [72, 202, 9, 9]],
  gemeos: [[48, 240, 9, 22], [72, 240, 9, 22]],
  tornozelo: [[48, 280, 7, 6], [72, 280, 7, 6]],
  pe: [[47, 300, 9, 7], [73, 300, 9, 7]],
};

function corZona(count: number, max: number): string {
  if (!count) return "#eef2f6";
  const t = max > 0 ? count / max : 0;
  const lerp = (a: number, b: number) => Math.round(a + (b - a) * t);
  return `rgb(${lerp(254, 185)}, ${lerp(226, 28)}, ${lerp(226, 28)})`; // rosa claro → vermelho
}

function Silhueta({ titulo, pos, freq, max }: { titulo: string; pos: Record<string, El[]>; freq: Record<string, number>; max: number }) {
  const label = ZONAS.reduce<Record<string, string>>((a, z) => ((a[z.chave] = z.label), a), {});
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "#334155", marginBottom: 4 }}>{titulo}</div>
      <svg viewBox="0 0 120 320" width="120" height="320" role="img" aria-label={`Body map — ${titulo}`}>
        {/* silhueta base */}
        <g fill="#f1f5f9" stroke="#cbd5e1" strokeWidth="1">
          <circle cx="60" cy="22" r="15" />
          <rect x="40" y="44" width="40" height="72" rx="12" />
          <rect x="14" y="52" width="12" height="72" rx="6" />
          <rect x="94" y="52" width="12" height="72" rx="6" />
          <rect x="42" y="112" width="16" height="96" rx="7" />
          <rect x="62" y="112" width="16" height="96" rx="7" />
          <rect x="42" y="208" width="14" height="96" rx="6" />
          <rect x="64" y="208" width="14" height="96" rx="6" />
        </g>
        {/* zonas */}
        {Object.entries(pos).map(([chave, els]) =>
          els.map((e, i) => (
            <ellipse
              key={`${chave}-${i}`}
              cx={e[0]} cy={e[1]} rx={e[2]} ry={e[3]}
              fill={corZona(freq[chave] ?? 0, max)}
              stroke={freq[chave] ? "#b91c1c" : "#cbd5e1"}
              strokeWidth={freq[chave] ? 1 : 0.5}
              opacity={freq[chave] ? 0.92 : 0.5}
            >
              <title>{label[chave] ?? chave}: {freq[chave] ?? 0} lesão(ões)</title>
            </ellipse>
          ))
        )}
      </svg>
    </div>
  );
}

export function BodyMap({ freq }: { freq: Record<string, number> }) {
  const max = Math.max(1, ...Object.values(freq));
  return (
    <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
      <Silhueta titulo="Frente" pos={FRENTE} freq={freq} max={max} />
      <Silhueta titulo="Costas" pos={COSTAS} freq={freq} max={max} />
    </div>
  );
}
