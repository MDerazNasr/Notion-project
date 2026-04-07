import { FeatureValue } from "@/lib/types";

type FeatureTableProps = {
  title: string;
  rows: FeatureValue[];
};

export function FeatureTable({ title, rows }: FeatureTableProps) {
  return (
    <section className="card p-5">
      <div className="mb-4">
        <div className="label mb-2">{title}</div>
        <h2 className="text-lg font-medium tracking-[-0.02em] text-ink">
          Feature breakdown
        </h2>
      </div>

      <div className="overflow-hidden rounded-subtle border border-line">
        {rows.map((row) => (
          <div
            key={row.name}
            className="grid grid-cols-[1fr_auto] gap-3 border-t border-line bg-white px-4 py-3 first:border-t-0"
          >
            <span className="text-sm font-medium capitalize text-ink">
              {row.name.replaceAll("_", " ")}
            </span>
            <span className="text-sm text-[color:var(--muted)]">
              {row.value.toFixed(4)}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
