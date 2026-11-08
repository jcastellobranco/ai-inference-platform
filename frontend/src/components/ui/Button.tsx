import { type ButtonHTMLAttributes } from 'react';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost';
};

export function Button({ variant = 'primary', type = 'button', className = '', ...props }: Props) {
  return <button type={type} className={[`button-${variant}`, className].filter(Boolean).join(' ')} {...props} />;
}
