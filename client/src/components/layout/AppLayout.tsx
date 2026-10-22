"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "./Sidebar";
import Link from "next/link";

export function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  // On login route, render standalone auth container without sidebar
  if (pathname === "/login") {
    return <main className="auth-shell">{children}</main>;
  }

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-main">
        <header className="app-topbar">
          <div className="topbar-breadcrumbs">
            <span className="crumb-segment">Workspace</span>
            <span className="crumb-separator">/</span>
            <span className="crumb-target">Acme Engineering</span>
            <span className="crumb-separator">/</span>
            <span className="crumb-badge">Production Gate</span>
          </div>

          <div className="topbar-actions">
            <div className="live-pill">
              <span className="live-indicator" />
              <span>Webhook Active</span>
            </div>
            <Link href="/pull-requests" className="btn btn-secondary btn-sm">
              Audits
            </Link>
            <Link href="/login" className="btn btn-outline btn-sm">
              Sign Out
            </Link>
          </div>
        </header>

        <main className="app-content">
          {children}
        </main>
      </div>
    </div>
  );
}
