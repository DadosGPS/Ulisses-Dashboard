"use client";

import { AlertStatus } from "@/lib/utils/alerts";
import { cores, raio, espaco } from "@/lib/theme";

interface StatusIndicatorProps {
  status: AlertStatus;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  compact?: boolean;
}

const statusConfig = {
  normal: {
    icon: "🟢",
    label: "Normal",
    color: "#22c55e",
    bgColor: "rgba(34, 197, 94, 0.12)",
  },
  attention: {
    icon: "🟡",
    label: "Atenção",
    color: "#eab308",
    bgColor: "rgba(234, 179, 8, 0.12)",
  },
  "high-attention": {
    icon: "🔴",
    label: "Atenção Alta",
    color: "#ef4444",
    bgColor: "rgba(239, 68, 68, 0.12)",
  },
};

const sizeConfig = {
  sm: { fontSize: "0.75rem", padding: "0.25rem 0.5rem" },
  md: { fontSize: "0.875rem", padding: "0.375rem 0.75rem" },
  lg: { fontSize: "1rem", padding: "0.5rem 1rem" },
};

export function StatusIndicator({
  status,
  size = "md",
  showLabel = true,
  compact = false,
}: StatusIndicatorProps) {
  const config = statusConfig[status];
  const sizeStyle = sizeConfig[size];

  if (compact) {
    return (
      <span style={{ fontSize: size === "sm" ? "0.875rem" : "1rem" }}>
        {config.icon}
      </span>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: espaco.xs,
        ...sizeStyle,
        borderRadius: raio.sm,
        background: config.bgColor,
        color: config.color,
        fontWeight: 600,
        whiteSpace: "nowrap",
      }}
    >
      <span>{config.icon}</span>
      {showLabel && <span>{config.label}</span>}
    </div>
  );
}

interface StatusBadgeProps {
  status: AlertStatus;
  count: number;
  onClick?: () => void;
}

export function StatusBadge({ status, count, onClick }: StatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <button
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: espaco.sm,
        padding: `${espaco.md}px ${espaco.lg}px`,
        borderRadius: raio.md,
        background: config.bgColor,
        border: `1px solid ${config.color}`,
        color: config.color,
        fontSize: "0.875rem",
        fontWeight: 600,
        cursor: onClick ? "pointer" : "default",
        transition: onClick ? "all 0.2s" : "none",
      }}
      onMouseEnter={(e) => {
        if (onClick) {
          (e.currentTarget as HTMLElement).style.opacity = "0.8";
        }
      }}
      onMouseLeave={(e) => {
        if (onClick) {
          (e.currentTarget as HTMLElement).style.opacity = "1";
        }
      }}
    >
      <span style={{ fontSize: "1.25rem" }}>{config.icon}</span>
      <div style={{ textAlign: "left" }}>
        <div>{config.label}</div>
        <div style={{ fontSize: "1.25rem", fontWeight: 700 }}>{count}</div>
      </div>
    </button>
  );
}
