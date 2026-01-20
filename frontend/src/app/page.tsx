"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";

import { Card, Metric, Text } from "@tremor/react";

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
  average_relevance_score: number;
  dominant_sentiment: string;
  top_platform: string | null;
};

type TrendsResponse = {
  days: number;
  points: { date: string; count: number }[];
};

type ChartData = {
  labels: string[];
  data: number[];
};

type ChartsResponse = {
  sentiment: ChartData;
  timeline: ChartData;
  platforms: ChartData;
  emotions: ChartData;
};

type ComparisonResponse = {
  share_of_voice: {
    brand_count: number;
    competitor_count: number;
    total: number;
    brand_percent: number;
    competitor_percent: number;
  };
  sentiment_benchmark: {
    brand_avg: number;
    competitor_avg: number;
  };
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
  const chartsKey = workspaceId
    ? `/api/v1/analytics/charts?workspace_id=${workspaceId}`
    : null;
  const comparisonKey = workspaceId
    ? `/api/v1/analytics/comparison?workspace_id=${workspaceId}`
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
  const { data: charts } = useSWR<ChartsResponse>(chartsKey, fetcher, {
    refreshInterval: 30000,
  });
  const { data: comparison } = useSWR<ComparisonResponse>(comparisonKey, fetcher, {
    refreshInterval: 30000,
  });
  const { data: history } = useSWR<HistoryResponse>(historyKey, fetcher, {
    refreshInterval: 30000,
  });

  const sentimentIndex = useMemo(() => {
    const labels = charts?.sentiment?.labels ?? [];
    const data = charts?.sentiment?.data ?? [];
    const counts = labels.reduce<Record<string, number>>((acc, label, idx) => {
      acc[label.toLowerCase()] = data[idx] ?? 0;
      return acc;
    }, {});
    const pos = counts.positive ?? 0;
    const neg = counts.negative ?? 0;
    const total = data.reduce((sum, value) => sum + (value ?? 0), 0);
    if (total === 0) return 0;
    return Math.round(((pos - neg) / total) * 100);
  }, [charts]);

  const topPlatform = useMemo(() => {
    const labels = charts?.platforms?.labels ?? [];
    const data = charts?.platforms?.data ?? [];
    if (labels.length === 0) return "N/A";
    const topIndex = data.reduce((bestIdx, value, idx) => {
      if ((value ?? 0) > (data[bestIdx] ?? 0)) {
        return idx;
      }
      return bestIdx;
    }, 0);
    return labels[topIndex] ?? "N/A";
  }, [charts]);

  const brandPercent = comparison?.share_of_voice?.brand_percent ?? 0;
  const competitorPercent = comparison?.share_of_voice?.competitor_percent ?? 0;
  const brandSentiment = comparison?.sentiment_benchmark?.brand_avg ?? 0;
  const competitorSentiment = comparison?.sentiment_benchmark?.competitor_avg ?? 0;

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
            <SentimentChart sentimentData={charts?.sentiment} />
          </div>
          <div className="lg:col-span-2">
            <TrendsChart points={trends?.points ?? []} days={days} />
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="bg-slate-950 text-slate-100 ring-1 ring-slate-800">
            <Text className="mb-2 text-slate-300">Share of Voice</Text>
            <div className="flex items-end justify-between">
              <div>
                <Text className="text-xs text-slate-400">Brand</Text>
                <Metric className="text-slate-100">{brandPercent.toFixed(1)}%</Metric>
              </div>
              <div className="text-right">
                <Text className="text-xs text-slate-400">Competitors</Text>
                <Metric className="text-slate-100">
                  {competitorPercent.toFixed(1)}%
                </Metric>
              </div>
            </div>
            <div className="mt-4 h-2 w-full rounded-full bg-slate-900">
              <div
                className="h-2 rounded-full bg-emerald-500"
                style={{ width: `${Math.min(100, Math.max(0, brandPercent))}%` }}
              />
            </div>
            <div className="mt-2 text-xs text-slate-500">
              {comparison?.share_of_voice?.brand_count ?? 0} brand vs{" "}
              {comparison?.share_of_voice?.competitor_count ?? 0} competitor
              mentions
            </div>
          </Card>
          <Card className="bg-slate-950 text-slate-100 ring-1 ring-slate-800">
            <Text className="mb-2 text-slate-300">Sentiment Benchmark</Text>
            <div className="flex items-end justify-between">
              <div>
                <Text className="text-xs text-slate-400">Brand Avg</Text>
                <Metric className="text-slate-100">{brandSentiment.toFixed(2)}</Metric>
              </div>
              <div className="text-right">
                <Text className="text-xs text-slate-400">Competitor Avg</Text>
                <Metric className="text-slate-100">
                  {competitorSentiment.toFixed(2)}
                </Metric>
              </div>
            </div>
            <div className="mt-3 text-xs text-slate-500">
              Scores: positive = 1, neutral = 0, negative = -1
            </div>
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2" id="mentions">
            <MentionsTable mentions={history?.mentions ?? []} />
          </div>
          <div className="lg:col-span-1" id="keywords">
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
                {(charts?.emotions?.labels ?? []).map((label, idx) => (
                  <li key={label} className="flex justify-between">
                    <span>{label}</span>
                    <span className="text-slate-400">{charts?.emotions?.data?.[idx] ?? 0}</span>
                  </li>
                ))}
                {(charts?.emotions?.labels?.length ?? 0) === 0 && (
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
