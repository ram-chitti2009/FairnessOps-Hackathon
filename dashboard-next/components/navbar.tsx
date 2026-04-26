"use client";
import { useEffect, useRef, useState } from "react";
import { RefreshCw, Activity, ChevronDown, LayoutGrid, Wifi, WifiOff } from "lucide-react";
import type { ModelContext } from "@/lib/registry";

interface Props {
  modelName: string;
  models: string[];
  ctx: ModelContext;
  realtimeStatus: "connecting" | "live" | "error";
  lastFetched: Date;
  loading: boolean;
  onRefresh: () => void;
  onModelChange: (model: string) => void;
}

export function Navbar({
  modelName,
  models,
  ctx,
  realtimeStatus,
  lastFetched,
  loading,
  onRefresh,
  onModelChange,
}: Props) {
  const [timeStr, setTimeStr]   = useState("");
  const [open, setOpen]         = useState(false);
  const dropdownRef             = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setTimeStr(
      lastFetched.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    );
  }, [lastFetched]);

  // Close dropdown on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Shorten a model name for display — strip trailing timestamp-like suffixes
  function displayName(name: string) {
    return name.replace(/_\d{14,}$/, "").replace(/_/g, " ");
  }

  const rt = {
    live: { label: "Live updates active", color: "text-green-400", Icon: Wifi },
    connecting: { label: "Connecting live updates", color: "text-amber-400", Icon: Wifi },
    error: { label: "Live updates offline", color: "text-red-400", Icon: WifiOff },
  }[realtimeStatus];

  return (
    <header className="sticky top-0 z-40 flex items-center h-14 px-6 border-b border-border bg-background/95 backdrop-blur-sm">
      {/* ── Brand ── */}
      <div className="flex items-center gap-2.5 flex-shrink-0">
        <Activity className="h-5 w-5 text-info flex-shrink-0" />
        <span className="text-sm font-bold text-text-primary tracking-tight">FairnessOps</span>
      </div>

      <span className="h-4 w-px bg-border mx-3 flex-shrink-0" />

      {/* ── Model selector ── */}
      <div className="relative flex-shrink-0" ref={dropdownRef}>
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-border bg-muted/30 hover:bg-muted/60 transition-colors"
          title="Switch model"
        >
          <LayoutGrid className="h-3.5 w-3.5 text-info flex-shrink-0" />
          <span className="text-xs font-semibold text-text-primary max-w-[180px] truncate">
            {displayName(modelName)}
          </span>
          <ChevronDown className={`h-3 w-3 text-text-muted transition-transform ${open ? "rotate-180" : ""}`} />
        </button>

        {open && (
          <div className="absolute top-full left-0 mt-1.5 z-50 min-w-[280px] max-w-[420px] rounded-lg border border-border bg-muted shadow-xl py-1">
            <p className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-widest text-text-muted border-b border-border/50 mb-1">
              Monitored Models ({models.length || "—"})
            </p>
            {models.length === 0 ? (
              <p className="px-3 py-2 text-xs text-text-muted italic">Loading…</p>
            ) : (
              models.map((m) => (
                <button
                  key={m}
                  onClick={() => { onModelChange(m); setOpen(false); }}
                  className={`w-full text-left px-3 py-2 text-xs transition-colors hover:bg-info/10 ${
                    m === modelName
                      ? "text-info font-semibold bg-info/5"
                      : "text-text-secondary"
                  }`}
                >
                  <span className="block font-medium">{displayName(m)}</span>
                  <span className="block font-mono text-[10px] text-text-muted mt-0.5 truncate">{m}</span>
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {/* ── Clinical context (secondary info) ── */}
      <div className="hidden md:flex items-center gap-2 ml-4 min-w-0">
        <span className="text-xs text-text-secondary truncate max-w-[160px]">{ctx.population}</span>
        <span className="text-xs text-text-muted">·</span>
        <span className="text-xs text-text-muted truncate max-w-[120px]">{ctx.department}</span>
      </div>

      {/* ── Right side ── */}
      <div className="ml-auto flex items-center gap-4 flex-shrink-0">
        <div className={`hidden lg:flex items-center gap-1.5 text-[11px] ${rt.color}`}>
          <rt.Icon className="h-3.5 w-3.5" />
          <span>{rt.label}</span>
        </div>
        {timeStr && (
          <span className="text-xs text-text-muted hidden sm:block">Updated {timeStr}</span>
        )}
        <button
          onClick={onRefresh}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-info/10 border border-info/30 text-info text-xs font-semibold hover:bg-info/20 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>
    </header>
  );
}
