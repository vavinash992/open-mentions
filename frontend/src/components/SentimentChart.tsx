"use client";

import { Card, Text } from "@tremor/react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

type ChartData = {
  labels: string[];
  data: number[];
};

type SentimentChartProps = {
  sentimentData?: ChartData;
};

export function SentimentChart({ sentimentData }: SentimentChartProps) {
  const counts = (sentimentData?.labels ?? []).reduce<Record<string, number>>(
    (acc, label, idx) => {
      acc[label.toLowerCase()] = sentimentData?.data?.[idx] ?? 0;
      return acc;
    },
    {},
  );

  const data = [
    { name: "positive", value: counts.positive ?? 0 },
    { name: "negative", value: counts.negative ?? 0 },
    { name: "neutral", value: counts.neutral ?? 0 },
  ];

  return (
    <Card className="bg-slate-950 text-slate-100 ring-1 ring-slate-800">
      <Text className="mb-4 text-slate-300">Sentiment Breakdown</Text>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius="60%"
              outerRadius="90%"
              stroke="transparent"
            >
              <Cell fill="#34d399" />
              <Cell fill="#fb7185" />
              <Cell fill="#facc15" />
            </Pie>
            <Tooltip
              formatter={(value: number) => value}
              contentStyle={{ background: "#0f172a", border: "1px solid #1f2937" }}
              labelStyle={{ color: "#e2e8f0" }}
              itemStyle={{ color: "#e2e8f0" }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-4 flex flex-wrap gap-3 text-xs text-slate-300">
        <span className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
          Positive
        </span>
        <span className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-rose-400" />
          Negative
        </span>
        <span className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-amber-300" />
          Neutral
        </span>
      </div>
    </Card>
  );
}
