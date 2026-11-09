import { type HTMLAttributes, type ReactNode } from 'react';

function Root({ children, onBackdropClick, ...props }: HTMLAttributes<HTMLDivElement> & {
  children: ReactNode; onBackdropClick?: () => void;
}) {
  return <div {...props} className={['dialog-backdrop', props.className].filter(Boolean).join(' ')}
    onMouseDown={event => { if (event.target === event.currentTarget) onBackdropClick?.(); props.onMouseDown?.(event); }}>{children}</div>;
}
function Content({ children, labelledBy, ...props }: HTMLAttributes<HTMLElement> & {
  children: ReactNode; labelledBy: string;
}) {
  return <section {...props} role="dialog" aria-modal="true" aria-labelledby={labelledBy}
    className={['access-dialog', props.className].filter(Boolean).join(' ')}>{children}</section>;
}
export const Dialog = { Root, Content };
