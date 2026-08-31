import {
  Database,
  History,
  Home,
  Menu,
  PlayCircle,
  SearchCheck,
  X,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";

const navigation = [
  { to: "/", label: "Início", icon: Home, end: true },
  { to: "/workflow", label: "Nova conciliação", icon: PlayCircle },
  { to: "/datasets", label: "Fontes de dados", icon: Database },
  { to: "/review", label: "Pendências", icon: SearchCheck },
  { to: "/audit", label: "Histórico", icon: History },
];

export function AppShell({ children }: { children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? "sidebar--open" : ""}`}>
        <div className="brand">
          <span className="brand__mark" aria-hidden="true">
            RF
          </span>
          <span>
            <strong>Reconcile</strong>Flow
            <small>Operações financeiras</small>
          </span>
          <button
            className="icon-button sidebar__close"
            onClick={() => setMobileOpen(false)}
            aria-label="Fechar navegação"
          >
            <X size={20} />
          </button>
        </div>
        <nav className="primary-nav" aria-label="Navegação principal">
          <p className="nav-label">Área de trabalho</p>
          {navigation.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `nav-link ${isActive ? "nav-link--active" : ""}`
              }
            >
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar__footer">
          <p>Fluxo operacional</p>
          <strong>
            Preparar · Comparar
            <br />
            Resolver · Exportar
          </strong>
          <Link className="sidebar-guide-link" to="/#como-funciona">
            Como usar
          </Link>
        </div>
      </aside>
      {mobileOpen && (
        <button
          className="sidebar-backdrop"
          onClick={() => setMobileOpen(false)}
          aria-label="Fechar navegação"
        />
      )}
      <div className="workspace">
        <header className="topbar">
          <button
            className="icon-button menu-button"
            onClick={() => setMobileOpen(true)}
            aria-label="Abrir navegação"
          >
            <Menu size={21} />
          </button>
          <span className="topbar__context">Conciliação e evidências</span>
          <span className="topbar__spacer" />
          <span className="environment-label">
            <i /> Ambiente local
          </span>
        </header>
        <main className="main-content">{children}</main>
      </div>
    </div>
  );
}
