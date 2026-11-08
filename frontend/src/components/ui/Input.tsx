import { type InputHTMLAttributes } from 'react';
import { useField } from './Field';

export function Input({ id, 'aria-describedby': describedBy, 'aria-invalid': invalid, className = '', ...props }: InputHTMLAttributes<HTMLInputElement>) {
  const field = useField();
  const ids = [describedBy, field.invalid ? field.errorId : undefined].filter(Boolean).join(' ') || undefined;
  return <input id={id ?? field.id} aria-describedby={ids} aria-invalid={invalid ?? (field.invalid || undefined)}
    className={['ui-input', className].filter(Boolean).join(' ')} {...props} />;
}
