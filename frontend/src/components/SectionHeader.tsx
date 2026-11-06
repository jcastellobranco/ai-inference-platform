import type { ReactNode } from 'react';
interface Props { eyebrow?: string; title: string; description?: string; action?: ReactNode }
export function SectionHeader({ eyebrow, title, description, action }: Props) {
  return <div className="content-header">
    <div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}
      <h2>{title}</h2>{description && <p>{description}</p>}
    </div>
    {action && <div className="content-header-action">{action}</div>}
  </div>;
}
