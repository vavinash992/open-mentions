"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";

import { KeywordManager } from "@/components/KeywordManager";
import { MentionsTable } from "@/components/MentionsTable";
import { SentimentChart } from "@/components/SentimentChart";
import { Sidebar } from "@/components/Sidebar";
import { StatCards } from "@/components/StatCards";
import { TrendsChart } from "@/components/TrendsChart";
import { fetcher } from "@/lib/api";
import { useWorkspace } from "@/hooks/useWorkspace";

type SummaryResponse = {
  total_mentions: number;
  sentiment_breakdown: Record<string, number>;
  top_emotions: { emotion: string; count: number }[];
  platform_stats: Record<string, number>;
};

type TrendsResponse = {
  days: number;
  points: { date: string; count: number }[];
};

type HistoryResponse = {
  mentions: {
    keyword: string;
    platform: string;
    content: string;
    url: string;
    sentiment?: string | null;
    emotion?: string | null;
    summary?: string | null;
  }[];
};

export default function Home() {
  const { workspaceId, loading } = useWorkspace();
  const [days, setDays] = useState(7);

  const summaryKey = workspaceId
    ? `/api/v1/analytics/summary?workspace_id=${workspaceId}`
    : null;
  const trendsKey = workspaceId
    ? `/api/v1/analytics/trends?workspace_id=${workspaceId}&days=${days}`
    : null;
  const historyKey = workspaceId
    ? `/api/v1/history?workspace_id=${workspaceId}&page=1&page_size=10`
    : null;

  const { data: summary } = useSWR<SummaryResponse>(summaryKey, fetcher, {
    refreshInterval: 30000,
  });
  const { data: trends } = useSWR<TrendsResponse>(trendsKey, fetcher, {
    refreshInterval: 30000,
  });
  const { data: history } = useSWR<HistoryResponse>(historyKey, fetcher, {
    refreshInterval: 30000,
  });

  const sentimentIndex = useMemo(() => {
    if (!summary?.sentiment_breakdown) return 0;
    const pos = summary.sentiment_breakdown.positive ?? 0;
    const neg = summary.sentiment_breakdown.negative ?? 0;
    return Math.round(pos - neg);
  }, [summary]);

  const topPlatform = useMemo(() => {
    const stats = summary?.platform_stats ?? {};
    const entries = Object.entries(stats);
    if (entries.length === 0) return "N/A";
    return entries.sort((a, b) => b[1] - a[1])[0][0];
  }, [summary]);

  return (
    <div className="flex min-h-screen bg-slate-950">
      <Sidebar />
      <main className="flex-1 space-y-8 px-8 py-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold">Dashboard</h2>
            <p className="text-sm text-slate-400">
              Workspace: {loading ? "Loading..." : workspaceId}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setDays(7)}
              className={`rounded-md px-3 py-1 text-xs ${
                days === 7 ? "bg-emerald-500 text-white" : "bg-slate-900 text-slate-300"
              }`}
            >
              7d
            </button>
            <button
              onClick={() => setDays(30)}
              className={`rounded-md px-3 py-1 text-xs ${
                days === 30 ? "bg-emerald-500 text-white" : "bg-slate-900 text-slate-300"
              }`}
            >
              30d
            </button>
          </div>
        </div>

        <StatCards
          totalMentions={summary?.total_mentions ?? 0}
          sentimentIndex={sentimentIndex}
          topPlatform={topPlatform}
        />

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-1">
            <SentimentChart sentimentBreakdown={summary?.sentiment_breakdown ?? {}} />
          </div>
          <div className="lg:col-span-2">
            <TrendsChart points={trends?.points ?? []} days={days} />
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2" id="mentions">
            <MentionsTable mentions={history?.mentions ?? []} />
          </div>
          <div className="lg:col-span-1">
            {workspaceId ? (
              <KeywordManager workspaceId={workspaceId} />
            ) : (
              <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-slate-500">
                Loading workspace...
              </div>
            )}
            <div className="mt-4 rounded-lg border border-slate-800 bg-slate-950 p-4">
              <div className="text-sm text-slate-300">Top Emotions</div>
              <ul className="mt-3 space-y-2 text-sm text-slate-200">
                {summary?.top_emotions?.map((emotion) => (
                  <li key={emotion.emotion} className="flex justify-between">
                    <span>{emotion.emotion}</span>
                    <span className="text-slate-400">{emotion.count}</span>
                  </li>
                ))}
                {(summary?.top_emotions?.length ?? 0) === 0 && (
                  <li className="text-slate-500">No data yet.</li>
                )}
              </ul>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
