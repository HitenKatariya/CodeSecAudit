"use client";

import React, { useState } from "react";
import {
  ShieldCheckIcon,
  AlertTriangleIcon,
  FileTextIcon,
  GitPullRequestIcon,
  ExternalLinkIcon,
  ZoomInIcon,
  CloseIcon,
  GitHubIcon,
} from "@/components/ui/Icons";

interface DemoItem {
  id: string;
  title: string;
  category: "gate" | "inline" | "integrations";
  categoryLabel: string;
  badge: {
    label: string;
    variant: "blocked" | "passed" | "warning" | "low" | "neutral";
  };
  description: string;
  src: string;
  liveUrl?: string;
  liveLabel?: string;
  highlights: string[];
}

const DEMO_ITEMS: DemoItem[] = [
  {
    id: "severe-pr",
    title: "Severe PR Review — Merge Gate Blocked",
    category: "gate",
    categoryLabel: "PR Security Gate",
    badge: {
      label: "MERGE BLOCKED",
      variant: "blocked",
    },
    description:
      "Autonomous security gate blocks merge when critical vulnerabilities are found. Generates an executive triage matrix, exact file coordinates, and OWASP-grounded remediation recommendations.",
    src: "/screenshots/github_pr_review_severe.png",
    liveUrl: "https://github.com/HitenKatariya/CodeSecAudit/pull/13",
    liveLabel: "View PR #13 on GitHub",
    highlights: ["CVSS 9.89 / 10.0 Risk Score", "Fails GitHub Check Run", "Executive Triage Matrix"],
  },
  {
    id: "healthy-pr",
    title: "Healthy PR Review — Merge Approved",
    category: "gate",
    categoryLabel: "PR Security Gate",
    badge: {
      label: "SECURITY PASSED",
      variant: "passed",
    },
    description:
      "Clean pull requests passing all OWASP Top 10 and AST taint analysis receive an immediate green approval check with zero false positives.",
    src: "/screenshots/github_pr_review_healthy.png",
    highlights: ["Zero Vulnerabilities Detected", "100% Policy Adherence", "Check Run Passed"],
  },
  {
    id: "inline-bugs",
    title: "Inline Vulnerability Taint Annotation",
    category: "inline",
    categoryLabel: "Inline Code Review",
    badge: {
      label: "INLINE FINDINGS",
      variant: "warning",
    },
    description:
      "Posts precise line-by-line review comments directly on the GitHub PR diff, pinpointing untrusted sources connecting into dangerous execution sinks.",
    src: "/screenshots/github_pr_review_bugs.png",
    liveUrl: "https://github.com/HitenKatariya/CodeSecAudit/pull/14",
    liveLabel: "View PR #14 Inline Comments",
    highlights: ["Exact Diff Coordinates", "CWE-89 / SQLi Detection", "Source-to-Sink Path"],
  },
  {
    id: "inline-suggest",
    title: "AI-Powered 1-Click Code Remediation",
    category: "inline",
    categoryLabel: "Inline Code Review",
    badge: {
      label: "AI FIX SUGGESTION",
      variant: "low",
    },
    description:
      "Provides production-ready, one-click committable GitHub suggestion diffs parameterized to remediate the vulnerability on the spot.",
    src: "/screenshots/github_pr_review_suggest.png",
    liveUrl: "https://github.com/HitenKatariya/CodeSecAudit/pull/14",
    liveLabel: "View Fix Suggestion on GitHub",
    highlights: ["One-Click GitHub Commit", "Parameterized Queries", "Defense-in-Depth"],
  },
  {
    id: "email-summary",
    title: "Automated Lead Engineer Email Notification",
    category: "integrations",
    categoryLabel: "Integrations & Services",
    badge: {
      label: "GMAIL NOTIFICATION",
      variant: "neutral",
    },
    description:
      "Instant email digests delivered upon PR scan completion with severity breakdowns, finding counts, and direct review links.",
    src: "/screenshots/pr_review_gmail.png",
    highlights: ["Instant Event Delivery", "Severity Breakdown", "Direct PR Links"],
  },
  {
    id: "rag-swagger",
    title: "RAG & Semantic Retrieval Services",
    category: "integrations",
    categoryLabel: "Integrations & Services",
    badge: {
      label: "FASTAPI & QDRANT",
      variant: "neutral",
    },
    description:
      "High-performance FastAPI service providing vector search over 2,833 OWASP Cheat Sheets and CWE knowledge bases via Qdrant.",
    src: "/screenshots/codesecrag_api_swagger.png",
    liveUrl: "https://codesec-rag-xp4b.onrender.com/docs",
    liveLabel: "Open Swagger OpenAPI Docs",
    highlights: ["2,833 OWASP Documents", "Cosine Vector Search", "FastAPI Asynchronous API"],
  },
];

export function DemoScreenshotsShowcase() {
  const [selectedCategory, setSelectedCategory] = useState<"all" | "gate" | "inline" | "integrations">("all");
  const [activeModalItem, setActiveModalItem] = useState<DemoItem | null>(null);

  const filteredItems =
    selectedCategory === "all"
      ? DEMO_ITEMS
      : DEMO_ITEMS.filter((item) => item.category === selectedCategory);

  const getBadgeStyle = (variant: DemoItem["badge"]["variant"]) => {
    switch (variant) {
      case "blocked":
        return {
          backgroundColor: "var(--crit-bg)",
          color: "var(--crit-color)",
          borderColor: "var(--crit-border)",
        };
      case "passed":
        return {
          backgroundColor: "var(--pass-bg)",
          color: "var(--pass-color)",
          borderColor: "var(--pass-border)",
        };
      case "warning":
        return {
          backgroundColor: "rgba(245, 158, 11, 0.12)",
          color: "#f59e0b",
          borderColor: "rgba(245, 158, 11, 0.3)",
        };
      case "low":
        return {
          backgroundColor: "rgba(59, 130, 246, 0.12)",
          color: "#3b82f6",
          borderColor: "rgba(59, 130, 246, 0.3)",
        };
      default:
        return {
          backgroundColor: "var(--bg-surface)",
          color: "var(--text-muted)",
          borderColor: "var(--border-subtle)",
        };
    }
  };

  return (
    <section
      id="product-demos"
      style={{
        maxWidth: "1150px",
        margin: "3rem auto 1rem",
        padding: "0 1.5rem",
        width: "100%",
      }}
    >
      {/* Section Header */}
      <div style={{ textAlign: "center", marginBottom: "2rem" }}>
        <div className="section-tag" style={{ color: "var(--accent)" }}>
          LIVE PRODUCT SHOWCASE
        </div>
        <h2 className="section-title" style={{ fontSize: "1.75rem", marginBottom: "0.5rem" }}>
          See CodeSecAudit AI in Action
        </h2>
        <p style={{ color: "var(--text-muted)", fontSize: "0.88rem", maxWidth: "620px", margin: "0 auto" }}>
          Real pull request security gates, inline code annotations, and automated remediation on production GitHub repositories.
        </p>

        {/* Category Tabs */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "0.35rem",
            backgroundColor: "var(--bg-surface)",
            padding: "0.3rem",
            borderRadius: "8px",
            border: "1px solid var(--border-subtle)",
            marginTop: "1.5rem",
            flexWrap: "wrap",
            justifyContent: "center",
          }}
        >
          {(
            [
              { key: "all", label: "All Screenshots" },
              { key: "gate", label: "PR Security Gate" },
              { key: "inline", label: "Inline Reviews & Fixes" },
              { key: "integrations", label: "Services & APIs" },
            ] as const
          ).map((tab) => {
            const isActive = selectedCategory === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setSelectedCategory(tab.key)}
                style={{
                  padding: "0.45rem 0.9rem",
                  fontSize: "0.78rem",
                  fontWeight: 600,
                  borderRadius: "6px",
                  border: isActive ? "1px solid var(--border-light)" : "1px solid transparent",
                  backgroundColor: isActive ? "var(--bg-base)" : "transparent",
                  color: isActive ? "var(--text-main)" : "var(--text-muted)",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  fontFamily: "var(--font-mono)",
                }}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Grid of Screenshot Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
          gap: "1.5rem",
          width: "100%",
        }}
      >
        {filteredItems.map((item) => {
          const badgeStyle = getBadgeStyle(item.badge.variant);

          return (
            <div
              key={item.id}
              className="card"
              style={{
                display: "flex",
                flexDirection: "column",
                border: "1px solid var(--border-subtle)",
                borderRadius: "10px",
                overflow: "hidden",
                padding: "0",
                backgroundColor: "var(--bg-surface)",
                boxShadow: "var(--shadow-card)",
                transition: "transform 0.15s ease, border-color 0.15s ease",
              }}
            >
              {/* Image Preview Container */}
              <div
                style={{
                  position: "relative",
                  width: "100%",
                  height: "220px",
                  backgroundColor: "var(--bg-base)",
                  overflow: "hidden",
                  borderBottom: "1px solid var(--border-subtle)",
                  cursor: "zoom-in",
                }}
                onClick={() => setActiveModalItem(item)}
                title="Click to expand screenshot"
              >
                <img
                  src={item.src}
                  alt={item.title}
                  loading="lazy"
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    objectPosition: "top",
                    transition: "transform 0.25s ease",
                  }}
                  onMouseOver={(e) => {
                    e.currentTarget.style.transform = "scale(1.02)";
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.transform = "scale(1)";
                  }}
                />

                {/* Hover overlay hint */}
                <div
                  style={{
                    position: "absolute",
                    top: "0.6rem",
                    right: "0.6rem",
                    display: "flex",
                    alignItems: "center",
                    gap: "0.35rem",
                    padding: "0.25rem 0.55rem",
                    borderRadius: "6px",
                    backgroundColor: "rgba(0, 0, 0, 0.75)",
                    color: "#fff",
                    fontSize: "0.7rem",
                    fontFamily: "var(--font-mono)",
                    backdropFilter: "blur(4px)",
                  }}
                >
                  <ZoomInIcon size={12} />
                  <span>Click to Expand</span>
                </div>
              </div>

              {/* Card Body */}
              <div style={{ padding: "1.25rem", display: "flex", flexDirection: "column", flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.65rem", gap: "0.5rem" }}>
                  <span
                    style={{
                      display: "inline-block",
                      padding: "0.2rem 0.55rem",
                      borderRadius: "4px",
                      fontSize: "0.68rem",
                      fontWeight: 700,
                      fontFamily: "var(--font-mono)",
                      border: "1px solid",
                      ...badgeStyle,
                    }}
                  >
                    {item.badge.label}
                  </span>
                  <span style={{ fontSize: "0.72rem", color: "var(--text-dim)", fontFamily: "var(--font-mono)" }}>
                    {item.categoryLabel}
                  </span>
                </div>

                <h3
                  style={{
                    fontSize: "0.95rem",
                    fontWeight: 700,
                    color: "var(--text-main)",
                    marginBottom: "0.45rem",
                    lineHeight: 1.4,
                  }}
                >
                  {item.title}
                </h3>

                <p
                  style={{
                    fontSize: "0.78rem",
                    color: "var(--text-muted)",
                    lineHeight: 1.5,
                    marginBottom: "1rem",
                    flex: 1,
                  }}
                >
                  {item.description}
                </p>

                {/* Highlights tags */}
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginBottom: "1rem" }}>
                  {item.highlights.map((tag, idx) => (
                    <span
                      key={idx}
                      style={{
                        fontSize: "0.68rem",
                        fontFamily: "var(--font-mono)",
                        padding: "0.2rem 0.5rem",
                        borderRadius: "4px",
                        backgroundColor: "var(--bg-base)",
                        color: "var(--text-muted)",
                        border: "1px solid var(--border-subtle)",
                      }}
                    >
                      {tag}
                    </span>
                  ))}
                </div>

                {/* Footer Actions */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    paddingTop: "0.75rem",
                    borderTop: "1px solid var(--border-subtle)",
                    gap: "0.5rem",
                  }}
                >
                  <button
                    onClick={() => setActiveModalItem(item)}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.4rem",
                      background: "none",
                      border: "none",
                      color: "var(--text-main)",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      cursor: "pointer",
                      padding: 0,
                    }}
                  >
                    <ZoomInIcon size={14} />
                    <span>View Full Size</span>
                  </button>

                  {item.liveUrl && (
                    <a
                      href={item.liveUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.35rem",
                        fontSize: "0.75rem",
                        color: "var(--accent)",
                        fontWeight: 600,
                        textDecoration: "none",
                      }}
                    >
                      <GitHubIcon size={13} />
                      <span>{item.liveLabel || "View Live"}</span>
                      <ExternalLinkIcon size={12} />
                    </a>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Lightbox Modal */}
      {activeModalItem && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.85)",
            backdropFilter: "blur(6px)",
            zIndex: 9999,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "1.5rem",
          }}
          onClick={() => setActiveModalItem(null)}
        >
          <div
            style={{
              position: "relative",
              maxWidth: "1050px",
              width: "100%",
              maxHeight: "92vh",
              display: "flex",
              flexDirection: "column",
              backgroundColor: "var(--bg-surface)",
              borderRadius: "12px",
              border: "1px solid var(--border-light)",
              overflow: "hidden",
              boxShadow: "0 24px 48px rgba(0,0,0,0.5)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "1rem 1.25rem",
                borderBottom: "1px solid var(--border-subtle)",
                backgroundColor: "var(--bg-surface)",
              }}
            >
              <div>
                <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-main)", margin: 0 }}>
                  {activeModalItem.title}
                </h3>
                <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", margin: "0.25rem 0 0" }}>
                  {activeModalItem.description}
                </p>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                {activeModalItem.liveUrl && (
                  <a
                    href={activeModalItem.liveUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.35rem",
                      fontSize: "0.75rem",
                      padding: "0.35rem 0.75rem",
                      borderRadius: "6px",
                      backgroundColor: "var(--bg-base)",
                      border: "1px solid var(--border-light)",
                      color: "var(--text-main)",
                      textDecoration: "none",
                      fontWeight: 600,
                    }}
                  >
                    <GitHubIcon size={14} />
                    <span>Open PR on GitHub</span>
                    <ExternalLinkIcon size={12} />
                  </a>
                )}
                <button
                  onClick={() => setActiveModalItem(null)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    padding: "0.25rem",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    borderRadius: "4px",
                  }}
                  title="Close (Esc)"
                >
                  <CloseIcon size={20} />
                </button>
              </div>
            </div>

            {/* Modal Image Display */}
            <div
              style={{
                overflow: "auto",
                backgroundColor: "#0d1117",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: "1rem",
              }}
            >
              <img
                src={activeModalItem.src}
                alt={activeModalItem.title}
                style={{
                  maxWidth: "100%",
                  height: "auto",
                  borderRadius: "6px",
                  boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
                }}
              />
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
