"use client";

import { Card, LineChart, Text } from "@tremor/react";

type TrendPoint = {
  date: string;
  count: number;
};

type TrendsChartProps = {
  points: TrendPoint[];
  days: number;
};

export function TrendsChart({ points, days }: TrendsChartProps) {
  return (
    <Card className="bg-slate-950 text-slate-100 ring-1 ring-slate-800">
      <Text className="mb-4 text-slate-300">
        Mentions in last {days} days
      </Text>
      <LineChart
        data={points}
        index="date"
        categories={["count"]}
        colors={["emerald"]}
        className="h-64"
      />
    </Card>
  );
}
