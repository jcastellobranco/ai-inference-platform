import type { ReactNode } from 'react';
interface Props { icon: ReactNode; title: string; description: string; action?: ReactNode }
export function EmptyState({ icon, title, description, action }: Props) {
  return <div className="empty-state">
    <div className="empty-icon">{icon}</div><h3>{title}</h3><p>{description}</p>{action}
  </div>;
}
