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

export function Sidebar() {
  const pathname = usePathname();
  const [user, setUser] = React.useState<UserProfile | null>(null);

  React.useEffect(() => {
    fetchMe().then(setUser);
  }, []);

  const initials = user?.username ? user.username.slice(0, 2).toUpperCase() : "CS";
  const orgName = user?.organization_name || "Acme Engineering";
  const displayName = user?.username ? `${user.username} (${user.organization_role || "Member"})` : "User";

  return (
    <aside className="app-sidebar">
      <div className="sidebar-header">
        <span className="logo-badge">🛡️</span>
        <div>
          <div className="logo-text">CodeSecAudit AI</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>PR Security Gate</div>
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
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>GitHub Connected</span>
          </div>
          <span style={{ fontSize: "0.7rem", color: "var(--text-dim)", background: "rgba(255,255,255,0.05)", padding: "2px 6px", borderRadius: "4px" }}>Active</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.65rem", paddingTop: "0.5rem", borderTop: "1px solid var(--border-subtle)" }}>
          <div style={{ width: "28px", height: "28px", borderRadius: "50%", background: "#1e293b", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.75rem", fontWeight: "bold", color: "var(--accent)" }}>
            {initials}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: "0.8rem", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{orgName}</div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-dim)" }}>{displayName}</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
