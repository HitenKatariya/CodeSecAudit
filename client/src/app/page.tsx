"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ShieldIcon,
  ShieldCheckIcon,
  GitPullRequestIcon,
  AlertTriangleIcon,
  PolicyIcon,
  RepoIcon,
  TrendingUpIcon,
  GitHubIcon,
  CheckCircleIcon,
} from "@/components/ui/Icons";
import { Button } from "@/components/ui/Button";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import {
  fetchMe,
  loginUser,
  fetchRepositories,
  fetchPullRequests,
  GITHUB_APP_INSTALL_URL,
  getGitHubAppInstallUrl,
} from "@/lib/api";
import { PullRequest, Repository, UserProfile } from "@/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { MetricCard } from "@/components/ui/MetricCard";
import { Card } from "@/components/ui/Card";
import { RepositoriesTable } from "@/components/repositories/RepositoriesTable";
import { RecentPRsTable } from "@/components/dashboard/RecentPRsTable";

const PR_AGENT_SKILLS = [
  {
    icon: <GitPullRequestIcon size={22} className="text-accent" />,
    badge: "AST TAINT ENGINE",
    title: "Source-to-Sink Dataflow Tracking",
    desc: "Traces untrusted user inputs (HTTP parameters, route params, body JSON) across function calls down to critical execution sinks (SQL queries, shell subprocesses, SSRF requests).",
  },
  {
    icon: <AlertTriangleIcon size={22} className="text-warning" />,
    badge: "CONTEXTUAL RAG",
    title: "OWASP Top 10 Grounding & CWE Mapping",
    desc: "Grounds every finding in high-dimensional vector embeddings of OWASP standards, CWE definitions, and real exploits. Eliminates LLM hallucinations.",
  },
  {
    icon: <PolicyIcon size={22} className="text-accent" />,
    badge: "ZERO-TRUST GATE",
    title: "Automated PR Check Runs & Merge Blocking",
    desc: "Automatically intercepts GitHub pull request events and evaluates organization security policies. Fails the check run if critical flaws or secrets are detected.",
  },
  {
    icon: <ShieldCheckIcon size={22} className="text-success" />,
    badge: "SECRET SCANNER",
    title: "High-Entropy Secret & Key Leak Detection",
    desc: "Scans diffs for leaked cloud tokens, AWS access keys, GitHub PATs, Stripe keys, and private credentials using Shannon entropy analysis.",
  },
  {
    icon: <TrendingUpIcon size={22} className="text-accent" />,
    badge: "LLM CONSENSUS",
    title: "Multi-Model Resilient Reasoning",
    desc: "Orchestrates ultra-fast inference with Groq Llama 3.3 70B, with automated zero-downtime failover to NVIDIA NIM and local heuristics.",
  },
  {
    icon: <RepoIcon size={22} className="text-accent" />,
    badge: "1-CLICK REMEDIATION",
    title: "Production-Ready Patch Generation",
    desc: "Produces inline Git diff recommendations with framework-idiomatic code fixes so developers can copy-paste and remediate instantly.",
  },
];

export default function HomePage() {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [repos, setRepos] = useState<Repository[]>([]);
  const [prs, setPrs] = useState<PullRequest[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);
  const [accountDeletedBanner, setAccountDeletedBanner] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const p = new URLSearchParams(window.location.search);
      if (p.get("deleted") === "true") {
        setAccountDeletedBanner(true);
        setIsInstalled(false);
        setUser(null);
        setRepos([]);
        setPrs([]);
        localStorage.clear();
      }
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    fetchMe()
      .then((profile) => {
        if (!isMounted) return;
        setUser(profile);
        if (profile) {
          loadDashboardData();
          if (profile.is_installed) {
            setIsInstalled(true);
            if (typeof window !== "undefined") {
              localStorage.setItem("codesec_app_installed", "true");
            }
          }
        } else {
          setLoading(false);
        }
      })
      .catch(() => {
        if (!isMounted) return;
        setUser(null);
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      const fromUrl = urlParams.get("installed") === "true";
      const fromStorage = localStorage.getItem("codesec_app_installed") === "true";
      if (fromUrl || fromStorage || user?.is_installed || repos.length > 0) {
        setIsInstalled(true);
        localStorage.setItem("codesec_app_installed", "true");
      }
    } else if (user?.is_installed || repos.length > 0) {
      setIsInstalled(true);
    }
  }, [user, repos]);


  const loadDashboardData = async () => {
    try {
      const [r, p] = await Promise.all([fetchRepositories(), fetchPullRequests()]);
      setRepos(r);
      setPrs(p);
    } catch (err) {
      console.error("Failed loading dashboard data:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleDemoSignIn = async () => {
    setLoading(true);
    const profile = await loginUser({ username: "admin", email: "admin@codesec.ai" });
    if (profile) {
      setUser(profile);
      await loadDashboardData();
    } else {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadDashboardData();
  };

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
        <span style={{ fontSize: "0.85rem", fontFamily: "var(--font-mono)" }}>
          Loading CodeSecAudit AI...
        </span>
      </div>
    );
  }

  // =========================================================================
  // VIEW 1: AUTHENTICATED USER -> SHOWCASE DASHBOARD
  // =========================================================================
  if (user) {
    const safeRepos = Array.isArray(repos) ? repos : [];
    const safePrs = Array.isArray(prs) ? prs : [];
    const totalFindings = safeRepos.reduce((acc, r) => acc + (r?.open_findings_count || 0), 0);
    const criticalCount = safeRepos.reduce((acc, r) => acc + (r?.critical_count || 0), 0);
    const blockedPrsCount = safePrs.filter((p) => p?.gate_status === "BLOCKED").length;
    const avgSecurityScore =
      safeRepos.length > 0
        ? Math.round(safeRepos.reduce((acc, r) => acc + (r?.security_score || 0), 0) / safeRepos.length)
        : 100;

    return (
      <div className="space-y">
        {/* Onboarding Banner only when app is NOT installed and no repos connected */}
        {!isInstalled && repos.length === 0 && (
          <div
            className="card"
            style={{
              background: "var(--bg-surface-elevated)",
              border: "1px solid var(--border-light)",
              padding: "1.75rem",
              borderRadius: "14px",
              boxShadow: "var(--shadow-card)",
            }}
          >
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div style={{ maxWidth: "680px" }}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="badge badge-warning">Step 1 Required</span>
                  <span className="text-xs font-mono text-muted">GitHub App Integration</span>
                </div>
                <h2 className="text-xl font-extrabold text-main mb-1.5 tracking-tight">
                  ⚡ Install the CodeSecAudit GitHub App
                </h2>
                <p className="text-xs text-muted leading-relaxed">
                  Connect your repositories to start receiving autonomous PR security audits. Once installed, every pull request is checked automatically against OWASP rules.
                </p>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <Button
                  variant="ghost"
                  size="md"
                  onClick={handleRefresh}
                  loading={refreshing}
                  className="font-mono text-xs"
                >
                  ↻ Refresh Repos
                </Button>
                <a href={getGitHubAppInstallUrl(user)} target="_blank" rel="noopener noreferrer">
                  <Button variant="primary" size="md" icon={<GitHubIcon size={16} />}>
                    Install GitHub App (1-Click) ↗
                  </Button>
                </a>
              </div>
            </div>
          </div>
        )}

        {/* When app is installed but waiting for first repo audit */}
        {isInstalled && repos.length === 0 && (
          <div
            className="card"
            style={{
              background: "var(--bg-surface-elevated)",
              border: "1px solid var(--border-light)",
              padding: "1.5rem",
              borderRadius: "14px",
              boxShadow: "var(--shadow-card)",
            }}
          >
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div
                  style={{
                    width: "42px",
                    height: "42px",
                    borderRadius: "10px",
                    background: "rgba(16, 185, 129, 0.15)",
                    color: "var(--color-success, #10b981)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  <CheckCircleIcon size={24} />
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="badge badge-passed">GitHub App Installed &amp; Active</span>
                    <span className="text-xs font-mono text-muted">Awaiting Pull Requests</span>
                  </div>
                  <p className="text-xs text-muted leading-relaxed">
                    CodeSecAudit AI is connected to your GitHub account. Open or synchronize a Pull Request in your repositories to trigger automatic AST taint analysis, OWASP RAG checks, and inline security comments.
                  </p>
                </div>
              </div>

              <Button
                variant="ghost"
                size="md"
                onClick={handleRefresh}
                loading={refreshing}
                className="font-mono text-xs shrink-0"
              >
                ↻ Refresh Status
              </Button>
            </div>
          </div>
        )}

        <PageHeader
          title="Security Posture Dashboard"
          subtitle="Real-time Pull Request risk assessment across active repositories."
          actions={
            <div className="flex items-center gap-2">
              {!isInstalled && repos.length === 0 && (
                <a href={getGitHubAppInstallUrl(user)} target="_blank" rel="noopener noreferrer">
                  <Button variant="secondary" size="md" icon={<GitHubIcon size={16} />}>
                    Install App ↗
                  </Button>
                </a>
              )}
              {isInstalled && (
                <span className="badge badge-passed text-xs font-mono py-1.5 px-3 flex items-center gap-1.5">
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: "currentColor", display: "inline-block" }} />
                  App Active
                </span>
              )}
              <Link href="/pull-requests">
                <Button variant="primary" size="md">
                  View All PRs →
                </Button>
              </Link>
            </div>
          }
        />


        {/* Attention Banner if blocked PRs */}
        {blockedPrsCount > 0 && (
          <div className="banner-alert">
            <div className="flex items-center gap-3">
              <AlertTriangleIcon size={20} className="text-critical shrink-0" />
              <div>
                <span className="font-bold text-main text-xs block">
                  Action Required: {blockedPrsCount} Pull Request(s) blocked by Security Policy
                </span>
                <span className="text-muted text-xs">
                  Vulnerabilities exceed your organization security thresholds. Merging is halted.
                </span>
              </div>
            </div>
            <Link href="/pull-requests">
              <Button variant="danger" size="sm">
                Review Blocked PRs
              </Button>
            </Link>
          </div>
        )}

        {/* Metric Cards Grid */}
        <div className="stat-grid">
          <MetricCard
            label="Avg Security Score"
            value={`${avgSecurityScore}/100`}
            trend="+3.2% vs last month"
            trendDirection="up"
          />
          <MetricCard
            label="Active Monitored Repos"
            value={repos.length}
            trend="100% webhook coverage"
            trendDirection="neutral"
          />
          <MetricCard
            label="Blocked PR Merges"
            value={blockedPrsCount}
            trend={blockedPrsCount > 0 ? "Policy gate active" : "Zero blockers"}
            trendDirection={blockedPrsCount > 0 ? "down" : "up"}
          />
          <MetricCard
            label="Open Vulnerabilities"
            value={totalFindings}
            trend={`${criticalCount} critical severity`}
            trendDirection={criticalCount > 0 ? "down" : "up"}
          />
        </div>

        {/* Tables */}
        <RecentPRsTable prs={prs} />
        <RepositoriesTable repositories={repos} />
      </div>
    );
  }

  // =========================================================================
  // VIEW 2: PUBLIC LANDING PAGE -> SHOWCASE PR AGENT SKILLS & GITHUB LOGIN
  // =========================================================================
  return (
    <div className="landing-shell">
      {/* Account Deletion Confirmation Banner */}
      {accountDeletedBanner && (
        <div
          style={{
            backgroundColor: "var(--pass-bg)",
            borderBottom: "1px solid var(--pass-border)",
            color: "var(--pass-color)",
            padding: "0.85rem 1.5rem",
            textAlign: "center",
            fontSize: "0.84rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "0.5rem",
          }}
        >
          <span>✓</span>
          <span>
            <strong>Account Successfully Deleted:</strong> Your account, GitHub App installation, and all security data have been wiped out cleanly. You can install fresh anytime!
          </span>
          <button
            onClick={() => setAccountDeletedBanner(false)}
            style={{ marginLeft: "1rem", background: "none", border: "none", color: "inherit", cursor: "pointer", fontWeight: "bold" }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Top Navbar strictly featuring Sign in with GitHub on right upper corner */}
      <header className="landing-nav">
        <div className="landing-nav-brand">
          <span className="logo-badge">🛡️</span>
          <div>
            <span className="logo-text">CodeSecAudit AI</span>
            <span
              style={{
                fontSize: "0.72rem",
                color: "var(--text-dim)",
                marginLeft: "0.5rem",
                fontFamily: "var(--font-mono)",
              }}
            >
              PR Security Gate
            </span>
          </div>
        </div>

        {/* Right Upper Corner: Theme Toggle & Strictly Sign in with GitHub */}
        <div className="landing-nav-actions">
          <ThemeToggle />
          <button
            onClick={handleDemoSignIn}
            className="btn btn-secondary btn-sm"
            title="Instant Demo Access"
            style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}
          >
            ⚡ Demo Access
          </button>
          <a href="/api/auth/github/start">
            <Button
              variant="primary"
              size="sm"
              icon={<GitHubIcon size={16} />}
              className="font-bold"
              style={{ padding: "0.45rem 1rem" }}
            >
              Sign in with GitHub
            </Button>
          </a>
        </div>
      </header>

      {/* Hero Section with Punchy Ragebait Hooks */}
      <section className="landing-hero">
        <div className="landing-hero-pill" style={{ borderColor: "rgba(239, 68, 68, 0.4)", color: "var(--crit-color)" }}>
          <span>🚨</span>
          <span>STILL TRUSTING &ldquo;LGTM 👍&rdquo;? ENJOY YOUR 3 AM BREACH NOTIFICATION.</span>
        </div>

        <h1 className="landing-hero-title">
          Stop Merging 80 IQ Pull Requests Into Production
        </h1>

        <p className="landing-hero-subtitle">
          Your peer review spent 20 minutes bikeshedding trailing commas while a subprocess shell injection and SQL concatenation slipped straight into main. CodeSecAudit AI blocks the merge in 8 seconds with authentic CVSS 0–10 severity scoring.
        </p>

        <div className="landing-hero-cta">
          <a href="/api/auth/github/start">
            <Button
              variant="primary"
              size="lg"
              icon={<GitHubIcon size={18} />}
              className="font-bold"
            >
              Sign in with GitHub
            </Button>
          </a>

          {!isInstalled && (
            <a href={getGitHubAppInstallUrl(user as UserProfile | null)} target="_blank" rel="noopener noreferrer">
              <Button variant="secondary" size="lg" icon={<RepoIcon size={18} />}>
                Install GitHub App (1-Click) ↗
              </Button>
            </a>
          )}
          {isInstalled && (
            <Link href="/dashboard">
              <Button variant="secondary" size="lg" icon={<CheckCircleIcon size={18} className="text-success" />}>
                Go to Dashboard →
              </Button>
            </Link>
          )}


          <Button
            variant="ghost"
            size="lg"
            onClick={handleDemoSignIn}
            className="font-mono text-xs"
            style={{ border: "1px dashed var(--border-light)" }}
          >
            ⚡ Instant Workspace Demo
          </Button>
        </div>

        {/* Live Audit Preview Card */}
        <div
          className="card text-left w-full"
          style={{
            maxWidth: "920px",
            background: "var(--bg-surface)",
            border: "1px solid var(--border-light)",
            padding: "1.5rem",
            boxShadow: "var(--shadow-card)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: "0.75rem",
              marginBottom: "1rem",
              paddingBottom: "0.75rem",
              borderBottom: "1px solid var(--border-subtle)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.65rem", flexWrap: "wrap" }}>
              <span className="badge badge-blocked">BLOCKED BY SECURITY GATE</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.78rem", color: "var(--text-muted)" }}>
                PR #482 &bull; payment-api/routes/charge.py
              </span>
            </div>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-dim)", whiteSpace: "nowrap" }}>
              AST Taint &bull; CWE-89 (SQL Injection)
            </span>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
              gap: "1rem",
              width: "100%",
            }}
          >
            <div
              style={{
                minWidth: 0,
                overflow: "hidden",
                borderRadius: "8px",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div
                style={{
                  padding: "0.45rem 0.85rem",
                  backgroundColor: "var(--crit-bg)",
                  borderBottom: "1px solid var(--crit-border)",
                  color: "var(--crit-color)",
                  fontSize: "0.74rem",
                  fontWeight: 700,
                  fontFamily: "var(--font-mono)",
                }}
              >
                ✕ Vulnerable Source-to-Sink Path (Diff)
              </div>
              <pre
                style={{
                  margin: 0,
                  padding: "0.85rem 1rem",
                  backgroundColor: "var(--bg-base)",
                  color: "var(--crit-color)",
                  fontSize: "0.78rem",
                  lineHeight: 1.6,
                  fontFamily: "var(--font-mono)",
                  overflowX: "auto",
                  whiteSpace: "pre",
                  boxSizing: "border-box",
                  minWidth: 0,
                }}
              >
{`- query = f"SELECT * FROM accounts WHERE id = '{req.args.get('id')}'"
- db.execute(query) # Unsanitized execution`}
              </pre>
            </div>

            <div
              style={{
                minWidth: 0,
                overflow: "hidden",
                borderRadius: "8px",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div
                style={{
                  padding: "0.45rem 0.85rem",
                  backgroundColor: "var(--pass-bg)",
                  borderBottom: "1px solid var(--pass-border)",
                  color: "var(--pass-color)",
                  fontSize: "0.74rem",
                  fontWeight: 700,
                  fontFamily: "var(--font-mono)",
                }}
              >
                ✓ Recommended OWASP Remediation (Auto-Patch)
              </div>
              <pre
                style={{
                  margin: 0,
                  padding: "0.85rem 1rem",
                  backgroundColor: "var(--bg-base)",
                  color: "var(--pass-color)",
                  fontSize: "0.78rem",
                  lineHeight: 1.6,
                  fontFamily: "var(--font-mono)",
                  overflowX: "auto",
                  whiteSpace: "pre",
                  boxSizing: "border-box",
                  minWidth: 0,
                }}
              >
{`+ query = "SELECT * FROM accounts WHERE id = :account_id"
+ db.execute(query, {"account_id": req.args.get("id")})`}
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* Ragebait Reality Check Section */}
      <section style={{ maxWidth: "1050px", margin: "2.5rem auto 1rem", padding: "0 1.5rem", width: "100%" }}>
        <div className="section-tag" style={{ color: "var(--crit-color)" }}>REALITY CHECK</div>
        <h2 className="section-title">Why Your Current PR Reviews Are an Incident Waiting to Happen</h2>
        
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1.25rem", marginTop: "1.5rem" }}>
          <div className="card" style={{ borderColor: "var(--border-subtle)" }}>
            <span style={{ fontSize: "1.5rem", display: "block", marginBottom: "0.5rem" }}>😴</span>
            <span className="badge badge-warning mb-2">THE TIRED SENIOR DEV</span>
            <h3 className="text-sm font-bold text-main mb-1.5">&ldquo;LGTM, ship it! 🚀&rdquo;</h3>
            <p className="text-xs text-muted leading-relaxed">
              Glanced at an 800-line diff on Friday at 5:42 PM. Scrolled to the bottom in 8 seconds, approved it to beat weekend traffic, and accidentally authorized remote code execution.
            </p>
          </div>

          <div className="card" style={{ borderColor: "var(--border-subtle)" }}>
            <span style={{ fontSize: "1.5rem", display: "block", marginBottom: "0.5rem" }}>🐇</span>
            <span className="badge badge-low mb-2">THE FLUFF AI REVIEWER</span>
            <h3 className="text-sm font-bold text-main mb-1.5">&ldquo;Consider renaming variable `x` to `counter`&rdquo;</h3>
            <p className="text-xs text-muted leading-relaxed">
              Spams your PR with 15 essays about PEP8 style guides and docstring formatting, while completely missing <code className="text-crit font-mono">cursor.execute(&quot;SELECT * &quot; + id)</code> on line 39. Peak noise, zero security.
            </p>
          </div>

          <div className="card" style={{ borderColor: "var(--accent)", backgroundColor: "var(--accent-glow)" }}>
            <span style={{ fontSize: "1.5rem", display: "block", marginBottom: "0.5rem" }}>🛡️</span>
            <span className="badge badge-passed mb-2">CODESECAUDIT AI</span>
            <h3 className="text-sm font-bold text-main mb-1.5">Zero Fluff. Cold, Mathematical CVSS Blocking.</h3>
            <p className="text-xs text-muted leading-relaxed">
              Doesn&apos;t care about your feelings or variable names. Pulls exact git diff coordinates, grounds CWEs with Qdrant vector retrieval, calculates an authentic <strong className="text-main">CVSS 9.89 / 10.0</strong>, and blocks the merge before exploit occurs.
            </p>
          </div>
        </div>
      </section>

      {/* PR Agent Skills Showcase */}
      <section className="skills-section">
        <div className="section-tag">AGENT CAPABILITIES</div>
        <h2 className="section-title">Core Skills of the PR Security Agent</h2>

        <div className="skills-grid">
          {PR_AGENT_SKILLS.map((skill, i) => (
            <div className="skill-card" key={i}>
              <div className="skill-card-icon">{skill.icon}</div>
              <div className="skill-card-badge">{skill.badge}</div>
              <h3 className="skill-card-title">{skill.title}</h3>
              <p className="skill-card-desc">{skill.desc}</p>
              <div className="pt-2 border-t border-subtle flex items-center gap-1.5 text-xs text-muted font-mono">
                <CheckCircleIcon size={14} className="text-success" />
                <span>Zero false-positive verified</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Installation Workflow Steps */}
      <section
        style={{
          padding: "3.5rem 1.5rem 5rem",
          maxWidth: "1050px",
          margin: "0 auto",
          width: "100%",
        }}
      >
        <div className="section-tag">SEAMLESS INTEGRATION</div>
        <h2 className="section-title">From Install to Protected in 60 Seconds</h2>

        <div className="grid-2 gap-4">
          <div className="card">
            <span className="badge badge-low mb-2">STEP 1</span>
            <h3 className="text-base font-bold text-main mb-1">1-Click Install GitHub App</h3>
            <p className="text-xs text-muted leading-relaxed mb-3">
              Add the <strong className="text-main">{(user as UserProfile | null)?.github_app_slug || "CodeSecAudit"}</strong> GitHub App to your personal account or organization. Select which repositories you want audited.
            </p>
            {!isInstalled && (
              <a href={getGitHubAppInstallUrl(user as UserProfile | null)} target="_blank" rel="noopener noreferrer">
                <Button variant="secondary" size="sm" icon={<GitHubIcon size={14} />}>
                  Install App on GitHub ↗
                </Button>
              </a>
            )}
            {isInstalled && (
              <div className="text-xs font-mono text-success flex items-center gap-1.5 font-bold">
                <CheckCircleIcon size={14} />
                Installed &amp; Active
              </div>
            )}

          </div>

          <div className="card">
            <span className="badge badge-passed mb-2">STEP 2</span>
            <h3 className="text-base font-bold text-main mb-1">Automatic PR Review Webhooks</h3>
            <p className="text-xs text-muted leading-relaxed mb-3">
              Every opened or updated pull request automatically triggers the CodeSec agent. Reviews land directly in GitHub Check Runs and PR comments within 15 seconds.
            </p>
            <div className="text-xs font-mono text-muted flex items-center gap-2">
              <span className="w-2 h-2 rounded-full" style={{ background: "var(--pass-color)" }} />
              Webhook listener active on Render
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer
        style={{
          borderTop: "1px solid var(--border-subtle)",
          padding: "2rem",
          textAlign: "center",
          fontSize: "0.78rem",
          color: "var(--text-dim)",
          fontFamily: "var(--font-mono)",
        }}
      >
        <span>CodeSecAudit AI &bull; Autonomous DevSecOps Pull Request Gate &bull; Built with Next.js & FastAPI</span>
      </footer>
    </div>
  );
}
