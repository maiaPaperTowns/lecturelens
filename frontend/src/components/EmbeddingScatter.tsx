import {
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CLUSTER_PALETTE } from "../lib/labels";
import type { ClusterDetail } from "../types";

interface Point {
  x: number;
  y: number;
  name: string;
  difficulty: string;
}

export function EmbeddingScatter({ clusters }: { clusters: ClusterDetail[] }) {
  const series = clusters.map((cluster, index) => ({
    key: cluster.id,
    label: cluster.label.length > 22 ? `${cluster.label.slice(0, 22)}...` : cluster.label,
    color: CLUSTER_PALETTE[index % CLUSTER_PALETTE.length],
    data: cluster.points.map<Point>((p) => ({
      x: Number(p.x.toFixed(2)),
      y: Number(p.y.toFixed(2)),
      name: p.name,
      difficulty: p.difficulty_label ?? "n/a",
    })),
  }));

  const allPoints = series.flatMap((s) => s.data);
  if (allPoints.length === 0) {
    return (
      <p className="p-6 text-center text-sm text-ink-faint">
        Not enough concepts to plot an embedding map.
      </p>
    );
  }

  const pad = 6;
  const xs = allPoints.map((p) => p.x);
  const ys = allPoints.map((p) => p.y);
  const xDomain: [number, number] = [Math.min(...xs) - pad, Math.max(...xs) + pad];
  const yDomain: [number, number] = [Math.min(...ys) - pad, Math.max(...ys) + pad];

  return (
    <div className="h-[380px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e6eaf3" />
          <XAxis
            type="number"
            dataKey="x"
            name="dim-1"
            tick={{ fontSize: 11 }}
            domain={xDomain}
            allowDecimals={false}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="dim-2"
            tick={{ fontSize: 11 }}
            domain={yDomain}
            allowDecimals={false}
          />
          <Tooltip
            cursor={{ strokeDasharray: "3 3" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const p = payload[0].payload as Point;
              return (
                <div className="card px-3 py-2 text-xs">
                  <p className="font-semibold text-ink">{p.name}</p>
                  <p className="text-ink-faint">difficulty: {p.difficulty}</p>
                </div>
              );
            }}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {series.map((s) => (
            <Scatter
              key={s.key}
              name={s.label}
              data={s.data}
              fill={s.color}
              isAnimationActive={false}
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
