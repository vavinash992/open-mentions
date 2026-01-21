"use client";

import { Card, Text } from "@tremor/react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type TrendsChartProps = {
  points: Array<Record<string, number | string>>;
  series: string[];
  days: number;
};

const LINE_COLORS = [
  "#34d399",
  "#60a5fa",
  "#facc15",
  "#f97316",
  "#a78bfa",
  "#f472b6",
  "#22d3ee",
  "#fb7185",
];

export function TrendsChart({ points, series, days }: TrendsChartProps) {
  const total = points.reduce((sum, point) => {
    return sum + series.reduce((acc, key) => acc + Number(point[key] ?? 0), 0);
  }, 0);
  const latestPoint = points[points.length - 1];
  const latestTotal = series.reduce((acc, key) => acc + Number(latestPoint?.[key] ?? 0), 0);
  const lastNonZero = [...points].reverse().find((point) =>
    series.some((key) => Number(point[key] ?? 0) > 0)
  );

  return (
    <Card className="bg-slate-950 text-slate-100 ring-1 ring-slate-800">
      <div className="mb-4 flex items-baseline justify-between">
        <Text className="text-slate-300">Mentions in last {days} days</Text>
        <div className="text-xs text-slate-400">
          Total: {total} · Latest ({latestPoint?.date ?? "—"}): {latestTotal}
          {lastNonZero && lastNonZero.date !== latestPoint?.date
            ? ` · Last active: ${lastNonZero.date}`
            : ""}
        </div>
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
            <CartesianGrid stroke="#1f2937" strokeDasharray="4 4" />
            <XAxis
              dataKey="date"
              tickFormatter={(value) => String(value).slice(5)}
              stroke="#64748b"
              tick={{ fontSize: 11 }}
            />
            <YAxis
              allowDecimals={false}
              stroke="#64748b"
              tick={{ fontSize: 11 }}
              label={{
                value: "Mentions",
                angle: -90,
                position: "insideLeft",
                fill: "#94a3b8",
                fontSize: 11,
              }}
            />
            <Tooltip
              formatter={(value: number) => `${value}`}
              labelFormatter={(label) => `Date: ${label}`}
              contentStyle={{ background: "#0f172a", border: "1px solid #1f2937" }}
              labelStyle={{ color: "#e2e8f0" }}
              itemStyle={{ color: "#e2e8f0" }}
            />
            {series.map((key, idx) => (
              <Line
                key={key}
                type="linear"
                dataKey={key}
                stroke={LINE_COLORS[idx % LINE_COLORS.length]}
                strokeWidth={2}
                dot={{ r: 2 }}
                activeDot={{ r: 4 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
