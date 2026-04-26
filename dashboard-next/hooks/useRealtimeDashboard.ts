"use client";
import { useEffect, useRef, useCallback } from "react";
import { supabase } from "@/lib/supabase";
import type { AlertRow } from "@/lib/types";

interface Options {
  modelName: string;
  /** Called when a new audit_run row is inserted — triggers a full data refresh. */
  onNewRun: () => void;
  /** Called with each newly inserted metric_alert row. */
  onNewAlert: (alert: AlertRow) => void;
}

/**
 * Subscribes to Supabase Realtime for:
 *  - fairnessops.audit_runs  INSERT  → fires onNewRun
 *  - fairnessops.metric_alerts INSERT → fires onNewAlert (filtered by model via run_id match)
 *
 * Both channels are cleaned up automatically on unmount.
 */
export function useRealtimeDashboard({ modelName, onNewRun, onNewAlert }: Options) {
  // Stable refs so channel callbacks don't re-subscribe on every render
  const onNewRunRef = useRef(onNewRun);
  const onNewAlertRef = useRef(onNewAlert);
  onNewRunRef.current = onNewRun;
  onNewAlertRef.current = onNewAlert;

  useEffect(() => {
    // Channel names include modelName so switching models creates fresh channels
    // rather than reusing a stale-named channel that Supabase may not fully flush.
    const runChanName   = `rt:audit_runs:${modelName}`;
    const alertChanName = `rt:metric_alerts:${modelName}`;

    // ── Channel 1: audit_runs ────────────────────────────────────────────
    const runChannel = supabase
      .channel(runChanName)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "fairnessops",
          table: "audit_runs",
          filter: `model_name=eq.${modelName}`,
        },
        () => {
          onNewRunRef.current();
        },
      )
      .subscribe();

    // ── Channel 2: metric_alerts ─────────────────────────────────────────
    // We can't filter by model_name directly (it's on audit_runs, not alerts)
    // so we receive all inserts and discard non-matching ones client-side.
    const alertChannel = supabase
      .channel(alertChanName)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "fairnessops",
          table: "metric_alerts",
        },
        (payload) => {
          const row = payload.new as AlertRow;
          if (row) onNewAlertRef.current(row);
        },
      )
      .subscribe();

    return () => {
      supabase.removeChannel(runChannel);
      supabase.removeChannel(alertChannel);
    };
  }, [modelName]); // only re-subscribe if modelName changes
}
