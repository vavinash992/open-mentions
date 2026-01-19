"use client";

import { Card, Metric, Text } from "@tremor/react";

type StatCardsProps = {
  totalMentions: number;
  sentimentIndex: number;
  topPlatform: string;
};

export function StatCards({
  totalMentions,
  sentimentIndex,
  topPlatform,
}: StatCardsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card className="bg-slate-950 text-slate-100 ring-1 ring-slate-800">
        <Text className="text-slate-400">Total Mentions</Text>
        <Metric className="text-slate-100">{totalMentions}</Metric>
      </Card>
      <Card className="bg-slate-950 text-slate-100 ring-1 ring-slate-800">
        <Text className="text-slate-400">Sentiment Index</Text>
        <Metric className="text-slate-100">{sentimentIndex}%</Metric>
        <Text className="text-xs text-slate-500">
          Positive % minus Negative %
        </Text>
      </Card>
      <Card className="bg-slate-950 text-slate-100 ring-1 ring-slate-800">
        <Text className="text-slate-400">Top Platform</Text>
        <Metric className="text-slate-100">{topPlatform}</Metric>
      </Card>
    </div>
  );
}
