"use client";

import { Card, Text } from "@tremor/react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  LabelList,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type TrendPoint = {
  date: string;
  count: number;
};

type TrendsChartProps = {
  points: TrendPoint[];
  days: number;
};

export function TrendsChart({ points, days }: TrendsChartProps) {
  const total = points.reduce((sum, point) => sum + (point.count ?? 0), 0);
  const latestPoint = points[points.length - 1];
  const lastNonZero = [...points].reverse().find((point) => point.count > 0);
  const valueFormatter = (value: number) => `${value}`;
  const labelRenderer = (props: { x?: number; y?: number; value?: number }) => {
    if (!props || !props.value || props.value <= 0) return null;
    const x = props.x ?? 0;
    const y = props.y ?? 0;
    return (
      <text x={x} y={y - 6} textAnchor="middle" fill="#e2e8f0" fontSize={10}>
        {props.value}
      </text>
    );
  };

  return (
    <Card className="bg-slate-950 text-slate-100 ring-1 ring-slate-800">
      <div className="mb-4 flex items-baseline justify-between">
        <Text className="text-slate-300">Mentions in last {days} days</Text>
        <div className="text-xs text-slate-400">
          Total: {total} · Latest ({latestPoint?.date ?? "—"}):{" "}
          {latestPoint?.count ?? 0}
          {lastNonZero && lastNonZero.date !== latestPoint?.date
            ? ` · Last active: ${lastNonZero.date} (${lastNonZero.count})`
            : ""}
        </div>
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={points} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
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
              formatter={(value: number) => valueFormatter(Number(value))}
              labelFormatter={(label) => `Date: ${label}`}
              contentStyle={{ background: "#0f172a", border: "1px solid #1f2937" }}
              labelStyle={{ color: "#e2e8f0" }}
              itemStyle={{ color: "#e2e8f0" }}
            />
            <Bar
              dataKey="count"
              fill="#10b981"
              opacity={0.2}
              barSize={10}
              radius={[4, 4, 0, 0]}
            />
            <Line
              type="linear"
              dataKey="count"
              stroke="#10b981"
              strokeWidth={2}
              dot={{ r: 3, stroke: "#10b981", fill: "#10b981" }}
              activeDot={{ r: 5 }}
            >
              <LabelList dataKey="count" content={labelRenderer} />
            </Line>
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
