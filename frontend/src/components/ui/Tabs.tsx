import { createContext, useContext, type ButtonHTMLAttributes, type ReactNode } from 'react';

type TabsContextValue = { value: string; onValueChange: (value: string) => void };
const TabsContext = createContext<TabsContextValue | null>(null);
function useTabs() {
  const value = useContext(TabsContext);
  if (!value) throw new Error('Tabs.Trigger must be rendered within Tabs.Root');
  return value;
}
function Root({ value, onValueChange, children, className = '' }: TabsContextValue & { children: ReactNode; className?: string }) {
  return <TabsContext.Provider value={{ value, onValueChange }}><div className={className}>{children}</div></TabsContext.Provider>;
}
function List({ children, 'aria-label': ariaLabel, className = '' }: { children: ReactNode; 'aria-label': string; className?: string }) {
  return <div role="group" aria-label={ariaLabel} className={className}>{children}</div>;
}
function Trigger({ value, className = '', onClick, ...props }: Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'value'> & { value: string }) {
  const tabs = useTabs();
  return <button type="button" aria-pressed={tabs.value === value} className={[className, tabs.value === value ? 'selected' : ''].filter(Boolean).join(' ')}
    onClick={event => { tabs.onValueChange(value); onClick?.(event); }} {...props} />;
}
export const Tabs = { Root, List, Trigger };
