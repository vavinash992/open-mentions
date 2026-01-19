"use client";

import { Card, DonutChart, Text } from "@tremor/react";

type SentimentChartProps = {
  sentimentBreakdown: Record<string, number>;
};

export function SentimentChart({ sentimentBreakdown }: SentimentChartProps) {
  const data = [
    { name: "positive", value: sentimentBreakdown.positive ?? 0 },
    { name: "negative", value: sentimentBreakdown.negative ?? 0 },
    { name: "neutral", value: sentimentBreakdown.neutral ?? 0 },
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
