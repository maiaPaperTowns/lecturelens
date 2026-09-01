import type { ReactNode } from "react";

export function SummaryCard({
  label,
  value,
  hint,
  icon,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  icon?: ReactNode;
}) {
  return (
    <div className="glass p-4">
      <div className="flex items-start justify-between">
        <p className="eyebrow">{label}</p>
        {icon && <span className="text-wine">{icon}</span>}
      </div>
      <p className="mt-2 font-display text-2xl font-medium text-ink">{value}</p>
      {hint && <p className="mt-1 text-xs text-ink-faint">{hint}</p>}
    </div>
  );
}
