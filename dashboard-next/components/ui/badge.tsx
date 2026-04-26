import * as React from "react";
import type { SeverityLevel } from "@/lib/types";
import { SEV_COLOR, SEV_BG, SEV_LABEL } from "@/lib/utils";

interface SeverityBadgeProps {
  severity: SeverityLevel | string;
  size?: "sm" | "md";
}

export function SeverityBadge({ severity, size = "md" }: SeverityBadgeProps) {
  const sev = (severity?.toUpperCase() ?? "INSUFFICIENT_DATA") as SeverityLevel;
  const color = SEV_COLOR[sev] ?? "#3d5a7a";
  const bg = SEV_BG[sev] ?? "#0a1520";
  const label = SEV_LABEL[sev] ?? sev;
  const dot = size === "sm" ? "h-1.5 w-1.5" : "h-2 w-2";
  const text = size === "sm" ? "text-[10px]" : "text-xs";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 font-semibold tracking-wide ${text}`}
      style={{ color, background: bg, border: `1px solid ${color}33` }}
    >
      <span className={`${dot} rounded-full`} style={{ background: color }} />
      {label}
    </span>
  );
}
