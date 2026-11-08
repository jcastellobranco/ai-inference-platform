import { type SelectHTMLAttributes, type OptionHTMLAttributes } from 'react';
import { useField } from './Field';

function Control({ id, 'aria-describedby': describedBy, 'aria-invalid': invalid, className = '', ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  const field = useField();
  const ids = [describedBy, field.invalid ? field.errorId : undefined].filter(Boolean).join(' ') || undefined;
  return <select id={id ?? field.id} aria-describedby={ids} aria-invalid={invalid ?? (field.invalid || undefined)}
    className={['ui-select', className].filter(Boolean).join(' ')} {...props} />;
}

function Option(props: OptionHTMLAttributes<HTMLOptionElement>) {
  return <option {...props} />;
}

export const Select = { Control, Option };
