import { type ButtonHTMLAttributes } from 'react';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'unstyled';
};

export function Button({ variant = 'primary', type = 'button', className = '', ...props }: Props) {
  const classes = [variant === 'unstyled' ? '' : `button-${variant}`, className].filter(Boolean).join(' ');
  return <button type={type} className={classes || undefined} {...props} />;
}
