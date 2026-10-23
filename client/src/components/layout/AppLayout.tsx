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
  const [loading, setLoading] = useState(pathname !== "/login");

  useEffect(() => {
    if (pathname === "/login") {
      setLoading(false);
      return;
    }

    let isMounted = true;
    fetchMe()
      .then((profile) => {
        if (!isMounted) return;
        if (!profile) {
          router.replace("/login");
        } else {
          setUser(profile);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!isMounted) return;
        router.replace("/login");
      });

    return () => {
      isMounted = false;
    };
  }, [pathname, router]);

  const handleSignOut = async () => {
    await logoutUser();
    setUser(null);
    router.replace("/login");
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
      <Sidebar user={user} onSignOut={handleSignOut} />
      <div className="app-main">
        <header className="app-topbar">
          <div className="topbar-breadcrumbs">
            <span className="crumb-segment">Enterprise</span>
            <span className="crumb-separator">/</span>
            <span className="crumb-target">{user?.organization_name || "CodeSec Workspace"}</span>
            <span className="crumb-separator">/</span>
            <span className="crumb-badge">Audit Gate</span>
          </div>

          <div className="topbar-actions">
            <div className="live-pill">
              <span className="live-indicator" />
              <span>Webhook Active</span>
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
