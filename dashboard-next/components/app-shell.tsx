"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Bell, FileCheck2, Gauge, GitCompareArrows, LayoutGrid, Lock, RefreshCw, Settings, ShieldCheck, UserRound, Wifi, WifiOff } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useDashboardData } from "@/hooks/useDashboardData";

const DEMO_ACCESS_CODE = process.env.NEXT_PUBLIC_DEMO_ACCESS_CODE ?? "";

const NAV_ITEMS = [
  { href: "/overview", label: "Overview", icon: LayoutGrid },
  { href: "/incidents", label: "Incidents", icon: Bell },
  { href: "/models", label: "Models", icon: Gauge },
  { href: "/drift", label: "Drift", icon: GitCompareArrows },
  { href: "/compliance", label: "Compliance", icon: FileCheck2 },
  { href: "/settings", label: "Settings", icon: Settings },
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const {
    modelName,
    models,
    ctx,
    realtimeStatus,
    lastFetched,
    loading,
    refresh,
    setModelName,
    roleMode,
    setRoleMode,
    alerts,
  } = useDashboardData();
  const [accessCode, setAccessCode] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  // Default to unlocked when no access code is configured; read localStorage in an
  // effect to avoid SSR/hydration mismatch (window is not available server-side).
  const [isUnlocked, setIsUnlocked] = useState<boolean>(!DEMO_ACCESS_CODE);

  useEffect(() => {
    if (!DEMO_ACCESS_CODE) return;
    try {
      setIsUnlocked(window.localStorage.getItem("fairnessops_demo_unlock") === "1");
    } catch {
      // no-op
    }
  }, []);

  const rt = {
    live: { label: "Live updates active", color: "text-green-400", Icon: Wifi },
    connecting: { label: "Connecting live updates", color: "text-amber-400", Icon: Wifi },
    error: { label: "Live updates offline", color: "text-red-400", Icon: WifiOff },
  }[realtimeStatus];

  const criticalCount = useMemo(() => alerts.filter((a) => a.severity === "RED").length, [alerts]);
  const warningCount = useMemo(() => alerts.filter((a) => a.severity === "YELLOW").length, [alerts]);

  return (
    <div className="min-h-screen bg-background text-text-primary">
      {!isUnlocked && (
        <div className="fixed inset-0 z-[100] bg-[#030b16]/95 backdrop-blur-sm flex items-center justify-center px-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-surface p-6 space-y-4">
            <h2 className="text-lg font-semibold text-text-primary">Secure demo access</h2>
            <p className="text-sm text-text-muted">Enter access code to view the clinical operations dashboard.</p>
            <input
              type="password"
              value={accessCode}
              onChange={(e) => {
                setAccessCode(e.target.value);
                setAuthError(null);
              }}
              onKeyDown={(e) => {
                if (e.key !== "Enter") return;
                if (accessCode.trim() === DEMO_ACCESS_CODE) {
                  setIsUnlocked(true);
                  try {
                    window.localStorage.setItem("fairnessops_demo_unlock", "1");
                  } catch {
                    // no-op
                  }
                } else {
                  setAuthError("Invalid access code.");
                }
              }}
              className="w-full bg-muted border border-border text-text-secondary text-sm rounded-md px-3 py-2 focus:outline-none focus:border-info"
              placeholder="Access code"
            />
            {authError && <p className="text-xs text-critical">{authError}</p>}
            <button
              onClick={() => {
                if (accessCode.trim() === DEMO_ACCESS_CODE) {
                  setIsUnlocked(true);
                  try {
                    window.localStorage.setItem("fairnessops_demo_unlock", "1");
                  } catch {
                    // no-op
                  }
                } else {
                  setAuthError("Invalid access code.");
                }
              }}
              className="w-full px-3 py-2 rounded-md bg-info/15 border border-info/40 text-info text-sm font-semibold hover:bg-info/25 transition-colors"
            >
              Enter dashboard
            </button>
          </div>
        </div>
      )}

      <div className="flex min-h-screen">
        <aside className="hidden lg:flex lg:w-64 xl:w-72 border-r border-border bg-[#081325] flex-col">
          <div className="h-16 border-b border-border flex items-center px-4 gap-2">
            <Activity className="h-5 w-5 text-info" />
            <div>
              <p className="text-sm font-bold">FairnessOps</p>
              <p className="text-[11px] text-text-muted">Clinical Ops Console</p>
            </div>
          </div>
          <nav className="p-3 space-y-1.5">
            {NAV_ITEMS.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                    isActive
                      ? "bg-info/10 text-info border border-info/30"
                      : "text-text-secondary hover:text-text-primary hover:bg-muted/30 border border-transparent"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
          <div className="mt-auto p-3 border-t border-border space-y-2">
            <div className="rounded-md border border-border bg-muted/20 p-2">
              <p className="text-[11px] text-text-muted">Current model</p>
              <p className="text-xs font-semibold truncate">{modelName}</p>
            </div>
            <div className="rounded-md border border-border bg-muted/20 p-2">
              <p className="text-[11px] text-text-muted">Latest run urgency</p>
              <p className="text-xs text-critical">Immediate review: {criticalCount}</p>
              <p className="text-xs text-warning">Monitor closely: {warningCount}</p>
            </div>
          </div>
        </aside>

        <div className="flex-1 min-w-0">
          <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur-sm">
            <div className="h-16 px-4 sm:px-6 flex items-center gap-3">
              <ShieldCheck className="h-4 w-4 text-info hidden sm:block" />
              <div className="min-w-0">
                <p className="text-sm font-semibold truncate">{ctx.useCase}</p>
                <p className="text-[11px] text-text-muted truncate">{ctx.population} · {ctx.department}</p>
              </div>

              <div className="ml-auto flex items-center gap-2 flex-wrap justify-end">
                <select
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  className="bg-muted border border-border text-text-secondary text-xs rounded-md px-3 py-1.5 focus:outline-none focus:border-info max-w-[220px]"
                  aria-label="Model selector"
                >
                  {models.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
                <select
                  value={roleMode}
                  onChange={(e) => setRoleMode(e.target.value as "Clinical Admin" | "Data Science" | "Compliance")}
                  className="bg-muted border border-border text-text-secondary text-xs rounded-md px-3 py-1.5 focus:outline-none focus:border-info"
                  aria-label="Role mode selector"
                >
                  <option value="Clinical Admin">Clinical Admin</option>
                  <option value="Data Science">Data Science</option>
                  <option value="Compliance">Compliance</option>
                </select>
                <div className={`hidden md:flex items-center gap-1.5 text-[11px] ${rt.color}`}>
                  <rt.Icon className="h-3.5 w-3.5" />
                  <span>{rt.label}</span>
                </div>
                <button
                  onClick={refresh}
                  disabled={loading}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-info/10 border border-info/30 text-info text-xs font-semibold hover:bg-info/20 disabled:opacity-50 transition-colors"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
                  Refresh
                </button>
              </div>
            </div>

            <div className="px-4 sm:px-6 py-2 border-t border-border/60 text-xs text-text-muted flex items-center gap-3">
              <UserRound className="h-3.5 w-3.5 text-text-secondary" />
              <span>Role mode: {roleMode}</span>
              <span>·</span>
              <span suppressHydrationWarning>Updated {lastFetched.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>
              {DEMO_ACCESS_CODE && (
                <>
                  <span>·</span>
                  <button
                    onClick={() => {
                      try {
                        window.localStorage.removeItem("fairnessops_demo_unlock");
                      } catch {
                        // no-op
                      }
                      setIsUnlocked(false);
                      setAccessCode("");
                    }}
                    className="inline-flex items-center gap-1 text-text-secondary hover:text-text-primary"
                  >
                    <Lock className="h-3.5 w-3.5" />
                    Lock dashboard
                  </button>
                </>
              )}
            </div>
          </header>

          <main className="px-4 sm:px-6 py-6 pb-20 lg:pb-6">{children}</main>
        </div>
      </div>

      {/* Mobile bottom navigation — visible below lg breakpoint */}
      <nav className="lg:hidden fixed bottom-0 inset-x-0 z-40 bg-[#081325]/95 backdrop-blur-sm border-t border-border flex items-stretch h-14">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex flex-1 flex-col items-center justify-center gap-0.5 text-[10px] font-medium transition-colors ${
                isActive ? "text-info" : "text-text-muted hover:text-text-secondary"
              }`}
            >
              <Icon className="h-4.5 w-4.5" style={{ width: "18px", height: "18px" }} />
              <span>{item.label}</span>
              {isActive && <span className="absolute bottom-0 block h-0.5 w-8 rounded-full bg-info" />}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
