"use client";

import React from "react";
import {
  GitHubIcon,
  ShieldCheckIcon,
  GitPullRequestIcon,
  AlertTriangleIcon,
  PolicyIcon,
} from "@/components/ui/Icons";
import { Button } from "@/components/ui/Button";

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
              Connect your GitHub account to start auditing pull requests.
            </p>
          </div>

          <a href="/api/auth/github/start" className="w-full">
            <Button
              variant="primary"
              size="lg"
              className="w-full font-bold auth-github-btn"
              icon={<GitHubIcon size={18} />}
            >
              Continue with GitHub
            </Button>
          </a>

          <div className="auth-security-notes">
            <p>Protected with PKCE authorization and tenant-scoped sessions.</p>
            <p>Your browser never accesses or stores raw GitHub API credentials.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
