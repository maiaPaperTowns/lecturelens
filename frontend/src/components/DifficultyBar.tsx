import { DIFFICULTY_COLORS } from "../lib/labels";
import type { DifficultyLabel } from "../types";

const ORDER: DifficultyLabel[] = ["easy", "medium", "hard"];

export function DifficultyBar({
  distribution,
  height = 8,
}: {
  distribution: Record<string, number>;
  height?: number;
}) {
  const total = ORDER.reduce((sum, key) => sum + (distribution[key] ?? 0), 0);
  if (total === 0) {
    return <div className="rounded-full bg-line/60" style={{ height }} />;
  }
  return (
    <div className="flex overflow-hidden rounded-full" style={{ height }} role="img" aria-label="Difficulty distribution">
      {ORDER.map((key) => {
        const count = distribution[key] ?? 0;
        if (count === 0) return null;
        return (
          <div
            key={key}
            style={{ width: `${(count / total) * 100}%`, backgroundColor: DIFFICULTY_COLORS[key] }}
            title={`${key}: ${count}`}
          />
        );
      })}
    </div>
  );
}
