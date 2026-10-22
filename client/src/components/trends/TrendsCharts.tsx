"use client";

import React, { useState } from "react";
import { Card } from "@/components/ui/Card";
import { AnalyticsTrends } from "@/types";

interface Props {
  trends?: AnalyticsTrends | null;
}

export function TrendsCharts({ trends }: Props) {
  const [hoveredMonth, setHoveredMonth] = useState<string | null>(null);

  const scoreData =
    trends?.score_progression && trends.score_progression.length > 0
      ? trends.score_progression
      : [{ month: "Current", score: trends?.security_score ?? 100 }];

  const categoryData =
    trends?.cwe_distribution && trends.cwe_distribution.length > 0
      ? trends.cwe_distribution
      : [
          {
            name: "Clean / No Vulnerabilities",
            cwe_id: "NONE",
            count: 0,
            pct: "100%",
            color: "var(--pass-color)",
            barBg: "rgba(34, 197, 94, 0.8)",
          },
        ];

  const totalFindings = categoryData.reduce((acc, c) => acc + (c.count || 0), 0);

  return (
    <div className="grid-2">
      {/* Monthly Security Score Progression */}
      <Card
        title="Security Score Progression"
        description="Average security posture across repositories"
        actions={
          <span className="badge badge-passed">
            Score: {trends?.security_score ?? 100}/100
          </span>
        }
      >
        <div
          className="flex items-end justify-between h-48 pt-6 px-3 border-b"
          style={{ borderColor: "var(--border-subtle)" }}
        >
          {scoreData.map((item) => {
            const isHovered = hoveredMonth === item.month;
            const barHeight = Math.max(12, Math.round((item.score / 100) * 120));

            return (
              <div
                key={item.month}
                className="flex flex-col items-center flex-1 cursor-pointer"
                onMouseEnter={() => setHoveredMonth(item.month)}
                onMouseLeave={() => setHoveredMonth(null)}
              >
                <span
                  className="text-xs font-mono font-bold mb-1"
                  style={{
                    color: isHovered ? "var(--accent)" : "var(--text-muted)",
                    transform: isHovered ? "scale(1.15)" : "scale(1)",
                    transition: "all 0.15s ease",
                  }}
                >
                  {item.score}
                </span>

                <div
                  style={{
                    height: `${barHeight}px`,
                    width: "36px",
                    borderRadius: "4px 4px 0 0",
                    background: isHovered
                      ? "var(--accent)"
                      : "linear-gradient(to top, rgba(56, 189, 248, 0.2), rgba(56, 189, 248, 0.7))",
                    border: "1px solid rgba(56, 189, 248, 0.4)",
                    transition: "all 0.2s ease",
                  }}
                />

                <span
                  className="text-xs mt-2 font-medium"
                  style={{
                    color: isHovered ? "var(--text-main)" : "var(--text-dim)",
                  }}
                >
                  {item.month}
                </span>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Vulnerabilities by Category */}
      <Card
        title="Vulnerabilities by Category"
        description="Distribution of detected CWE patterns in database"
        actions={
          <span className="text-xs text-dim font-mono">
            {totalFindings} total detected
          </span>
        }
      >
        <div className="flex flex-col gap-3.5 pt-1">
          {categoryData.map((cat) => (
            <div key={cat.name} className="flex flex-col gap-1">
              <div className="flex-between text-xs">
                <span
                  className="font-medium"
                  style={{ color: "var(--text-main)" }}
                >
                  {cat.name}
                </span>
                <span
                  className="font-mono"
                  style={{ color: "var(--text-muted)" }}
                >
                  {cat.count}{" "}
                  <span style={{ color: "var(--text-dim)" }}>
                    ({cat.pct})
                  </span>
                </span>
              </div>

              <div
                style={{
                  height: "8px",
                  width: "100%",
                  background: "var(--bg-surface-elevated)",
                  borderRadius: "999px",
                  overflow: "hidden",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: cat.pct,
                    background: cat.barBg,
                    borderRadius: "999px",
                    transition: "width 0.5s ease",
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
