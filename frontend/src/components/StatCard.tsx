import type { ReactNode } from 'react';
interface Props { label: string; value: string | number; meta: string; icon: ReactNode; tone?: string }
export function StatCard({ label, value, meta, icon, tone = 'blue' }: Props) {
  return <article className="stat-card">
    <div className={`stat-icon tone-${tone}`}>{icon}</div>
    <p className="stat-label">{label}</p>
    <strong className="stat-value">{value}</strong>
    <p className="stat-meta">{meta}</p>
  </article>;
}
