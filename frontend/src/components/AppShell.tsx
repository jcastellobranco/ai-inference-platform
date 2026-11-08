import type { ReactNode } from 'react';

export type View = 'overview' | 'documents' | 'playground' | 'agents' | 'jobs';
const routes: Array<{ id: View; label: string; symbol: string; hint: string }> = [
  { id: 'overview', label: 'Overview', symbol: '◫', hint: '01' },
  { id: 'documents', label: 'Knowledge base', symbol: '▤', hint: '02' },
  { id: 'playground', label: 'RAG playground', symbol: '✧', hint: '03' },
  { id: 'agents', label: 'Multi-Agent', symbol: '✳', hint: '04' },
  { id: 'jobs', label: 'Job runs', symbol: '◷', hint: '05' },
];
interface Props {
  view: View; onNavigate: (view: View) => void; connected: boolean;
  children: ReactNode; onOpenAccess: () => void;
}
export function AppShell({ view, onNavigate, connected, children, onOpenAccess }: Props) {
  return <div className="app-layout">
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">A<span>·</span></div>
        <div><strong>ATLAS</strong><small>AI PLATFORM</small></div>
      </div>
      <div className="nav-label">WORKSPACE</div>
      <nav aria-label="Primary navigation" className="main-nav">
        {routes.map(route => <button key={route.id} type="button"
          className={`nav-link ${view === route.id ? 'active' : ''}`}
          aria-current={view === route.id ? 'page' : undefined}
          onClick={() => onNavigate(route.id)}>
          <span className="nav-symbol" aria-hidden="true">{route.symbol}</span>
          <span>{route.label}</span><span className="nav-hint">{route.hint}</span>
        </button>)}
      </nav>
      <div className="sidebar-bottom">
        <div className="sidebar-info"><span className="pulse" /> LOCAL WORKSPACE</div>
        <p>Developer environment</p>
        <button className="sidebar-access" type="button" onClick={onOpenAccess}>
          <span>◇</span> {connected ? 'Manage access' : 'Connect your JWT'} <span>↗</span>
        </button>
        <p className="sidebar-caption">RAG · AGENTS · MCP · EVALUATION</p>
      </div>
    </aside>
    <div className="main-column">
      <header className="topbar">
        <div className="breadcrumbs"><span>Workspace</span><span>/</span>
          <strong>{routes.find(route => route.id === view)?.label}</strong>
        </div>
        <button className="connection-chip" type="button" onClick={onOpenAccess}>
          <span className={`connection-indicator ${connected ? 'connected' : ''}`} />
          {connected ? 'JWT connected' : 'Not connected'} <span>⌄</span>
        </button>
      </header>
      <main className="workspace-content">{children}</main>
      <footer className="app-footer">
        <span>ATLAS AI PLATFORM <span className="footer-separator">/</span> LOCAL DEMO</span>
        <span>Tenant-aware services · v0.2</span>
      </footer>
    </div>
  </div>;
}
