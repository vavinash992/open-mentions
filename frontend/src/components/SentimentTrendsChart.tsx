"use client";

import { AreaChart, Card, Text } from "@tremor/react";

type SentimentTrendPoint = {
    date: string;
    positive: number;
    negative: number;
    neutral: number;
};

type Props = {
    points: SentimentTrendPoint[];
};

export function SentimentTrendsChart({ points }: Props) {
    const chartData = points.map((p) => ({
        date: p.date,
        Positive: p.positive,
        Negative: p.negative,
        Neutral: p.neutral,
    }));

    return (
        <Card className="bg-slate-950 text-slate-100 ring-1 ring-slate-800">
            <Text className="text-slate-300">Sentiment Over Time</Text>
            <Text className="text-xs text-slate-500">
                Daily breakdown of positive, negative, and neutral mentions
            </Text>
            {chartData.length === 0 || chartData.every((d) => d.Positive + d.Negative + d.Neutral === 0) ? (
                <div className="mt-6 flex h-40 items-center justify-center text-sm text-slate-500">
                    No sentiment data yet.
                </div>
            ) : (
                <AreaChart
                    className="mt-4 h-48"
                    data={chartData}
                    index="date"
                    categories={["Positive", "Negative", "Neutral"]}
                    colors={["emerald", "rose", "slate"]}
                    showAnimation
                    curveType="monotone"
                    showLegend
                    showGridLines={false}
                    yAxisWidth={30}
                />
            )}
        </Card>
    );
}
