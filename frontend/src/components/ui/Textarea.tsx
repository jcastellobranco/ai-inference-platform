import { type TextareaHTMLAttributes } from 'react';
import { useField } from './Field';

export function Textarea({ id, 'aria-describedby': describedBy, 'aria-invalid': invalid, className = '', ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const field = useField();
  const ids = [describedBy, field.invalid ? field.errorId : undefined].filter(Boolean).join(' ') || undefined;
  return <textarea id={id ?? field.id} aria-describedby={ids} aria-invalid={invalid ?? (field.invalid || undefined)}
    className={['ui-textarea', className].filter(Boolean).join(' ')} {...props} />;
}
