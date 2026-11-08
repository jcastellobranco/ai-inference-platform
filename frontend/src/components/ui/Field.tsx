import { createContext, useContext, useId, type HTMLAttributes, type LabelHTMLAttributes, type ReactNode } from 'react';

type FieldContextValue = { id: string; descriptionId: string; errorId: string; invalid: boolean };
const FieldContext = createContext<FieldContextValue | null>(null);

export function useField() {
  const context = useContext(FieldContext);
  if (!context) throw new Error('Field compound components must be used within Field.Root');
  return context;
}

function Root({ children, id, invalid = false, className = '' }: {
  children: ReactNode; id?: string; invalid?: boolean; className?: string;
}) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;
  return <FieldContext.Provider value={{
    id: fieldId, descriptionId: `${fieldId}-description`, errorId: `${fieldId}-error`, invalid,
  }}><div className={`ui-field ${className}`.trim()}>{children}</div></FieldContext.Provider>;
}

function Label({ htmlFor, ...props }: LabelHTMLAttributes<HTMLLabelElement>) {
  const field = useField();
  return <label htmlFor={htmlFor ?? field.id} {...props} />;
}

function Description({ id, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  const field = useField();
  return <p id={id ?? field.descriptionId} className={['ui-field-description', props.className].filter(Boolean).join(' ')} {...props} />;
}

function ErrorMessage({ id, children, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  const field = useField();
  if (!children) return null;
  return <p id={id ?? field.errorId} role="alert" {...props} className={['ui-field-error', props.className].filter(Boolean).join(' ')}>{children}</p>;
}

export const Field = { Root, Label, Description, ErrorMessage };
