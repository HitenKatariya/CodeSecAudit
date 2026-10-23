"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  GitHubIcon,
  ShieldCheckIcon,
  GitPullRequestIcon,
  AlertTriangleIcon,
  PolicyIcon,
} from "@/components/ui/Icons";
import { Button } from "@/components/ui/Button";
import { fetchMe, loginUser } from "@/lib/api";

const FEATURES = [
  {
    icon: <GitPullRequestIcon size={18} />,
    title: "End-to-end AST Taint Analysis",
    body: "Every diff is traced from source to sink before it merges.",
  },
  {
    icon: <AlertTriangleIcon size={18} />,
    title: "OWASP Top 10 Contextual RAG",
    body: "Findings are grounded in real OWASP guidance, not guesswork.",
  },
  {
    icon: <PolicyIcon size={18} />,
    title: "Automated PR Check Run Blocking",
    body: "Risky merges are gated automatically, no manual review queue.",
  },
];

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("omchoksi");
  const [email, setEmail] = useState("om@codesec.ai");
  const [loading, setLoading] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    fetchMe()
      .then((user) => {
        if (!isMounted) return;
        if (user) {
          router.replace("/dashboard");
        } else {
          setCheckingSession(false);
        }
      })
      .catch(() => {
        if (!isMounted) return;
        setCheckingSession(false);
      });

    return () => {
      isMounted = false;
    };
  }, [router]);

  const handleDirectLogin = async (e?: React.FormEvent, customUser?: string, customEmail?: string) => {
    if (e) e.preventDefault();
    setError(null);
    setLoading(true);

    const targetUser = customUser || username.trim();
    const targetEmail = customEmail || email.trim();

    if (!targetUser) {
      setError("Please provide a username");
      setLoading(false);
      return;
    }

    try {
      const user = await loginUser({
        username: targetUser,
        email: targetEmail || undefined,
      });

      if (user) {
        router.replace("/dashboard");
      } else {
        setError("Sign in failed. Please verify the backend service is reachable.");
        setLoading(false);
      }
    } catch (err) {
      setError("An unexpected error occurred during sign in.");
      setLoading(false);
    }
  };

  if (checkingSession) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100vh",
          background: "var(--bg-canvas, #090d16)",
        }}
      >
        <div
          style={{
            width: "32px",
            height: "32px",
            border: "3px solid rgba(255,255,255,0.1)",
            borderTopColor: "var(--accent, #3b82f6)",
            borderRadius: "50%",
            animation: "spin 0.8s linear infinite",
          }}
        />
      </div>
    );
  }

  return (
    <div className="auth-split">
      <div className="auth-brand-pane">
        <div className="auth-brand-glow" aria-hidden="true" />
        <div className="auth-brand-content">
          <div className="auth-logo-mark">
            <ShieldCheckIcon size={22} />
          </div>
          <h1 className="auth-brand-title">CodeSecAudit AI</h1>
          <p className="auth-brand-tagline">
            Autonomous pull request security review and policy gate platform.
          </p>

          <div className="auth-feature-list">
            {FEATURES.map((f) => (
              <div className="auth-feature-row" key={f.title}>
                <div className="auth-feature-icon">{f.icon}</div>
                <div>
                  <div className="auth-feature-title">{f.title}</div>
                  <div className="auth-feature-body">{f.body}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="auth-trust-line">
            Installed as a GitHub App &middot; reviews land as a check run on every PR
          </div>
        </div>
      </div>

      <div className="auth-form-pane">
        <div className="auth-card">
          <div className="auth-card-header">
            <h2 className="auth-card-title">Sign in</h2>
            <p className="auth-card-subtitle">
              Sign in with your workspace account or continue with GitHub.
            </p>
          </div>

          {error && (
            <div
              style={{
                padding: "0.75rem",
                borderRadius: "6px",
                background: "rgba(239, 68, 68, 0.1)",
                border: "1px solid rgba(239, 68, 68, 0.25)",
                color: "var(--fail-color, #ef4444)",
                fontSize: "0.8rem",
              }}
            >
              {error}
            </div>
          )}

          <form onSubmit={handleDirectLogin} style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "0.3rem" }}>
                Username / Handle
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. HitenKatariya"
                required
                style={{
                  width: "100%",
                  padding: "0.6rem 0.75rem",
                  borderRadius: "6px",
                  background: "var(--bg-card, #0f172a)",
                  border: "1px solid var(--border-subtle, #334155)",
                  color: "var(--text-main, #f8fafc)",
                  fontSize: "0.85rem",
                  outline: "none",
                }}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "0.3rem" }}>
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="e.g. hitenvk22@gmail.com"
                style={{
                  width: "100%",
                  padding: "0.6rem 0.75rem",
                  borderRadius: "6px",
                  background: "var(--bg-card, #0f172a)",
                  border: "1px solid var(--border-subtle, #334155)",
                  color: "var(--text-main, #f8fafc)",
                  fontSize: "0.85rem",
                  outline: "none",
                }}
              />
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              disabled={loading}
              className="w-full font-bold"
            >
              {loading ? "Signing in..." : "Sign in to Workspace"}
            </Button>
          </form>

          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", margin: "0.25rem 0" }}>
            <div style={{ flex: 1, height: "1px", background: "var(--border-subtle, #334155)" }} />
            <span style={{ fontSize: "0.7rem", color: "var(--text-dim)", textTransform: "uppercase" }}>or</span>
            <div style={{ flex: 1, height: "1px", background: "var(--border-subtle, #334155)" }} />
          </div>

          <a href="/api/auth/github/start" className="w-full">
            <Button
              variant="secondary"
              size="lg"
              className="w-full font-bold auth-github-btn"
              icon={<GitHubIcon size={18} />}
            >
              Continue with GitHub
            </Button>
          </a>

          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              type="button"
              onClick={() => handleDirectLogin(undefined, "HitenKatariya", "hitenvk22@gmail.com")}
              className="btn btn-ghost btn-sm"
              style={{ flex: 1, fontSize: "0.75rem", border: "1px dashed var(--border-subtle)" }}
            >
              ⚡ Quick Sign in (Hiten)
            </button>
            <button
              type="button"
              onClick={() => handleDirectLogin(undefined, "omchoksi", "om@codesec.ai")}
              className="btn btn-ghost btn-sm"
              style={{ flex: 1, fontSize: "0.75rem", border: "1px dashed var(--border-subtle)" }}
            >
              ⚡ Quick Sign in (Om)
            </button>
          </div>

          <div className="auth-security-notes">
            <p>Protected with PKCE authorization and tenant-scoped sessions.</p>
            <p>Audit trail recorded in PostgreSQL on every authentication event.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
