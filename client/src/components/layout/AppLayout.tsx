"use client";

import React, { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { ThemeToggle } from "./ThemeToggle";
import Link from "next/link";
import { fetchMe, logoutUser } from "@/lib/api";
import { UserProfile } from "@/types";

export function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    let isMounted = true;
    fetchMe()
      .then((profile) => {
        if (!isMounted) return;
        setUser(profile);
        setLoading(false);
        if (!profile && pathname !== "/login" && pathname !== "/") {
          router.replace("/login");
        } else if (profile && pathname === "/") {
          router.replace("/dashboard");
        }
      })
      .catch(() => {
        if (!isMounted) return;
        setUser(null);
        setLoading(false);
        if (pathname !== "/login" && pathname !== "/") {
          router.replace("/login");
        }
      });

    return () => {
      isMounted = false;
    };
  }, [pathname, router]);

  const handleSignOut = async () => {
    await logoutUser();
    setUser(null);
    router.replace("/");
  };

  // On login route, render standalone auth container with fixed theme toggle
  if (pathname === "/login") {
    return (
      <main className="auth-shell">
        <div style={{ position: "fixed", top: "1.25rem", right: "1.25rem", zIndex: 50 }}>
          <ThemeToggle />
        </div>
        {children}
      </main>
    );
  }

  // On home landing route when unauthenticated, render public landing container without sidebar
  if (pathname === "/" && !user && !loading) {
    return <main className="landing-shell">{children}</main>;
  }

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100vh",
          background: "var(--bg-base)",
          color: "var(--text-muted)",
          gap: "1rem",
        }}
      >
        <div
          style={{
            width: "36px",
            height: "36px",
            border: "3px solid var(--border-light)",
            borderTopColor: "var(--accent)",
            borderRadius: "50%",
            animation: "spin 0.8s linear infinite",
          }}
        />
        <span style={{ fontSize: "0.85rem", fontFamily: "var(--font-mono)" }}>Verifying session...</span>
      </div>
    );
  }

  return (
    <div className="app-shell">
      {mobileOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}
      <Sidebar
        user={user}
        onSignOut={handleSignOut}
        isOpen={mobileOpen}
        onClose={() => setMobileOpen(false)}
      />
      <div className="app-main">
        <header className="app-topbar">
          <div className="topbar-breadcrumbs">
            <button
              className="mobile-menu-btn"
              onClick={() => setMobileOpen(!mobileOpen)}
              aria-label="Toggle navigation"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
            <span className="crumb-segment">CodeSec</span>
            <span className="crumb-separator">/</span>
            <span className="crumb-target">{user?.organization_name || user?.username || "Audit Gate"}</span>
          </div>

          <div className="topbar-actions">
            <div className="live-pill">
              <span className="live-indicator" />
              <span>Active</span>
            </div>
            <ThemeToggle />
            <Link href="/pull-requests" className="btn btn-secondary btn-sm">
              Audits
            </Link>
            <button
              onClick={handleSignOut}
              className="btn btn-outline btn-sm"
              title="Sign out"
            >
              Sign Out
            </button>
          </div>
        </header>

        <main className="app-content">{children}</main>
      </div>
    </div>
  );
}
