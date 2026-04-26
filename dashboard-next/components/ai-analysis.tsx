"use client";
import { Card, CardContent } from "@/components/ui/card";
import { parseLLMResponse } from "@/lib/utils";
import { Zap, AlertTriangle } from "lucide-react";

interface Props {
  text: string | null;
  error: string | null;
  loading: boolean;
}

export function AIAnalysis({ text, error, loading }: Props) {
  return (
    <Card className="border-[#1a0a3e] bg-gradient-to-br from-[#0d0820] to-[#060d1a]">
      <CardContent className="pt-5">
        <div className="flex items-center gap-2 mb-4">
          <Zap className="h-4 w-4 text-purple-400" />
          <span className="text-xs font-semibold uppercase tracking-widest text-purple-400">
            AI Clinical Briefing
          </span>
          <span className="ml-auto text-[10px] text-text-muted font-mono">GPT-4o-mini</span>
        </div>

        {loading && (
          <div className="space-y-2 animate-pulse">
            <div className="h-3 bg-muted rounded w-full" />
            <div className="h-3 bg-muted rounded w-5/6" />
            <div className="h-3 bg-muted rounded w-4/6" />
          </div>
        )}

        {error && !loading && (
          <div className="flex items-start gap-2 text-text-secondary">
            <AlertTriangle className="h-4 w-4 mt-0.5 text-yellow-600 flex-shrink-0" />
            <p className="text-sm">{error}</p>
          </div>
        )}

        {text && !loading && (() => {
          const { summary, actions } = parseLLMResponse(text);
          return (
            <div className="space-y-4">
              {summary && (
                <p className="text-sm leading-relaxed text-text-primary">{summary}</p>
              )}
              {actions.length > 0 && (
                <div className="space-y-2.5 border-t border-[#1a0a3e] pt-4">
                  <p className="text-xs font-semibold uppercase tracking-widest text-text-muted mb-3">
                    Suggested care-ops actions
                  </p>
                  {actions.map((a, i) => (
                    <div key={i} className="flex gap-3">
                      <span className="flex-shrink-0 mt-0.5 h-5 w-5 rounded-full bg-purple-900/50 border border-purple-700/50 text-purple-300 text-xs font-bold flex items-center justify-center">
                        {i + 1}
                      </span>
                      <div>
                        <span className="text-sm font-semibold text-purple-300">{a.label}: </span>
                        <span className="text-sm text-text-secondary">{a.body}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })()}
      </CardContent>
    </Card>
  );
}
