"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ShieldIcon,
  GitPullRequestIcon,
  RepoIcon,
  AlertTriangleIcon,
  TrendingUpIcon,
  PolicyIcon,
  FileTextIcon,
  UsersIcon,
  PlugIcon,
  SettingsIcon,
  TerminalIcon,
} from "../ui/Icons";
import { fetchMe } from "@/lib/api";
import { UserProfile } from "@/types";

interface NavLinkItem {
  name: string;
  href: string;
  icon: React.ReactNode;
}

const NAV_GROUPS: { group: string; items: NavLinkItem[] }[] = [
  {
    group: "OVERVIEW",
    items: [
      { name: "Dashboard", href: "/dashboard", icon: <ShieldIcon size={16} /> },
    ],
  },
  {
    group: "DEVELOPMENT",
    items: [
      { name: "Pull Requests", href: "/pull-requests", icon: <GitPullRequestIcon size={16} /> },
      { name: "Repositories", href: "/repositories", icon: <RepoIcon size={16} /> },
    ],
  },
  {
    group: "SECURITY",
    items: [
      { name: "Findings", href: "/findings", icon: <AlertTriangleIcon size={16} /> },
      { name: "Security Trends", href: "/trends", icon: <TrendingUpIcon size={16} /> },
    ],
  },
  {
    group: "MANAGEMENT",
    items: [
      { name: "Policies", href: "/policies", icon: <PolicyIcon size={16} /> },
      { name: "Reports", href: "/reports", icon: <FileTextIcon size={16} /> },
      { name: "Team", href: "/team", icon: <UsersIcon size={16} /> },
    ],
  },
  {
    group: "SYSTEM",
    items: [
      { name: "Integrations", href: "/integrations", icon: <PlugIcon size={16} /> },
      { name: "Settings", href: "/settings", icon: <SettingsIcon size={16} /> },
      { name: "Admin Logs", href: "/admin/logs", icon: <TerminalIcon size={16} /> },
    ],
  },
];

interface SidebarProps {
  user?: UserProfile | null;
  onSignOut?: () => void;
}

export function Sidebar({ user: propUser, onSignOut }: SidebarProps = {}) {
  const pathname = usePathname();
  const [internalUser, setInternalUser] = React.useState<UserProfile | null>(null);

  React.useEffect(() => {
    if (propUser === undefined) {
      fetchMe().then(setInternalUser);
    }
  }, [propUser]);

  const user = propUser !== undefined ? propUser : internalUser;
  const orgName = user?.username ? `@${user.username}` : user?.organization_name || "Personal Workspace";
  const roleDisplay = user?.organization_role ? (user.organization_role.toLowerCase() === "admin" ? "Account Owner" : user.organization_role) : "Developer";

  return (
    <aside className="app-sidebar">
      <div className="sidebar-header">
        <span className="logo-badge">🛡️</span>
        <div>
          <div className="logo-text">CodeSecAudit AI</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", fontFamily: "var(--font-mono)" }}>PR Security Gate</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV_GROUPS.map((grp) => (
          <div key={grp.group} style={{ marginBottom: "0.75rem" }}>
            <div className="nav-group-title">{grp.group}</div>
            {grp.items.map((item) => {
              const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`nav-item ${isActive ? "active" : ""}`}
                >
                  {item.icon}
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--pass-color)" }} />
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>GitHub Connected</span>
          </div>
          <span style={{ fontSize: "0.7rem", color: "var(--text-dim)", background: "var(--bg-surface-hover)", border: "1px solid var(--border-subtle)", padding: "2px 6px", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>Active</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.65rem", paddingTop: "0.5rem", borderTop: "1px solid var(--border-subtle)" }}>
          <div style={{ width: "28px", height: "28px", borderRadius: "50%", background: "var(--bg-surface-hover)", border: "1px solid var(--border-light)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.8rem", color: "var(--text-main)" }}>
            🛡️
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: "0.8rem", fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "var(--text-main)" }}>{orgName}</div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-dim)", fontFamily: "var(--font-mono)" }}>{roleDisplay}</div>
          </div>
          {onSignOut && (
            <button
              onClick={onSignOut}
              title="Sign Out"
              style={{
                background: "transparent",
                border: "none",
                color: "var(--text-dim)",
                cursor: "pointer",
                padding: "4px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                borderRadius: "4px",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "var(--fail-color)")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-dim)")}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
