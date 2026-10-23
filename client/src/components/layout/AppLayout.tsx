"use client";

import React, { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Sidebar } from "./Sidebar";
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

  // On login route, render standalone auth container without sidebar
  if (pathname === "/login") {
    return <main className="auth-shell">{children}</main>;
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
          background: "var(--bg-canvas, #090d16)",
          color: "var(--text-muted, #94a3b8)",
          gap: "1rem",
        }}
      >
        <div
          style={{
            width: "36px",
            height: "36px",
            border: "3px solid rgba(255,255,255,0.1)",
            borderTopColor: "var(--accent, #3b82f6)",
            borderRadius: "50%",
            animation: "spin 0.8s linear infinite",
          }}
        />
        <span style={{ fontSize: "0.85rem" }}>Verifying session...</span>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <Sidebar user={user} onSignOut={handleSignOut} />
      <div className="app-main">
        <header className="app-topbar">
          <div className="topbar-breadcrumbs">
            <span className="crumb-segment">Workspace</span>
            <span className="crumb-separator">/</span>
            <span className="crumb-target">{user?.organization_name || "Workspace"}</span>
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
            <button
              onClick={handleSignOut}
              className="btn btn-outline btn-sm"
              title="Sign out of CodeSecAudit"
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
