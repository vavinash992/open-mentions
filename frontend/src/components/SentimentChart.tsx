"use client";

import { Card, DonutChart, Text } from "@tremor/react";

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
      <DonutChart
        data={data}
        category="value"
        index="name"
        variant="donut"
        colors={["emerald", "rose", "slate"]}
        className="h-56"
      />
    </Card>
  );
}
