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
    keyword: string;
    category: string;
    count: number;
    percent: number;
  }[];
  sentiment_benchmark: {
    keyword: string;
    category: string;
    average_sentiment: number;
  }[];
  trends: Array<Record<string, number | string>>;
};

type ReachResponse = {
  estimated_reach: number;
  most_impactful: {
    url: string;
    platform: string;
    summary: string;
    keyword: string;
    impact_score: number;
  }[];
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
  const reachKey = workspaceId
    ? `/api/v1/analytics/reach?workspace_id=${workspaceId}`
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
  const { data: reach } = useSWR<ReachResponse>(reachKey, fetcher, {
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

  const sentimentByKeyword = useMemo(() => {
    const map = new Map<string, number>();
    (comparison?.sentiment_benchmark ?? []).forEach((item) => {
      map.set(item.keyword, item.average_sentiment);
    });
    return map;
  }, [comparison]);

  const leaderboard = useMemo(() => {
    const items = comparison?.share_of_voice ?? [];
    return [...items].sort((a, b) => b.percent - a.percent);
  }, [comparison]);

  const trendSeries = useMemo(() => {
    const items = comparison?.share_of_voice ?? [];
    return items.map((item) => item.keyword);
  }, [comparison]);

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
            <TrendsChart
              points={comparison?.trends ?? trends?.points ?? []}
              series={trendSeries}
              days={days}
            />
          </div>
        </div>

        <Card className="bg-slate-950 text-slate-100 ring-1 ring-slate-800">
          <div className="flex items-center justify-between">
            <Text className="text-slate-300">Share of Voice Leaderboard</Text>
            <div className="text-xs text-slate-500">Sentiment score: +1 to -1</div>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-800 text-slate-400">
                <tr>
                  <th className="px-2 py-2">Rank</th>
                  <th className="px-2 py-2">Keyword</th>
                  <th className="px-2 py-2">Category</th>
                  <th className="px-2 py-2">Sentiment</th>
                  <th className="px-2 py-2">SOV %</th>
                  <th className="px-2 py-2">Mentions</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((item, index) => (
                  <tr key={item.keyword} className="border-b border-slate-900 text-slate-200">
                    <td className="px-2 py-2 text-slate-300">{index + 1}</td>
                    <td className="px-2 py-2 text-slate-300">{item.keyword}</td>
                    <td className="px-2 py-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wide ${
                          item.category === "competitor"
                            ? "bg-rose-900/40 text-rose-300"
                            : "bg-emerald-900/40 text-emerald-300"
                        }`}
                      >
                        {item.category}
                      </span>
                    </td>
                    <td className="px-2 py-2 text-slate-300">
                      {(sentimentByKeyword.get(item.keyword) ?? 0).toFixed(2)}
                    </td>
                    <td className="px-2 py-2 text-slate-300">{item.percent.toFixed(2)}%</td>
                    <td className="px-2 py-2 text-slate-300">{item.count}</td>
                  </tr>
                ))}
                {leaderboard.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-center text-slate-500">
                      No comparison data yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        <Card className="bg-slate-950 text-slate-100 ring-1 ring-slate-800">
          <div className="flex items-center justify-between">
            <Text className="text-slate-300">Reach & Impact</Text>
            <div className="text-right">
              <Text className="text-xs text-slate-500">Estimated Reach</Text>
              <Metric className="text-slate-100">{reach?.estimated_reach ?? 0}</Metric>
            </div>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-800 text-slate-400">
                <tr>
                  <th className="px-2 py-2">Platform</th>
                  <th className="px-2 py-2">Summary</th>
                  <th className="px-2 py-2">Keyword</th>
                  <th className="px-2 py-2">Impact</th>
                  <th className="px-2 py-2">Source</th>
                </tr>
              </thead>
              <tbody>
                {(reach?.most_impactful ?? []).map((item) => (
                  <tr key={item.url} className="border-b border-slate-900 text-slate-200">
                    <td className="px-2 py-2 capitalize">{item.platform}</td>
                    <td className="px-2 py-2 text-slate-300">{item.summary}</td>
                    <td className="px-2 py-2 text-slate-300">{item.keyword}</td>
                    <td className="px-2 py-2 text-slate-300">{item.impact_score}</td>
                    <td className="px-2 py-2">
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-emerald-400 hover:underline"
                      >
                        View
                      </a>
                    </td>
                  </tr>
                ))}
                {(reach?.most_impactful?.length ?? 0) === 0 && (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-4 py-6 text-center text-slate-500"
                    >
                      No impact data yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

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
