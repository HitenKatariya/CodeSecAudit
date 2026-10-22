import React from "react";

export interface SecurityScoreGaugeProps {
  score: number;
  size?: number;
  strokeWidth?: number;
  trend?: string;
  trendDirection?: "up" | "down";
  showDetails?: boolean;
  className?: string;
}

export function SecurityScoreGauge({
  score,
  size = 120,
  strokeWidth = 9,
  trend,
  trendDirection = "up",
  showDetails = true,
  className = "",
}: SecurityScoreGaugeProps) {
  const normalizedScore = Math.max(0, Math.min(100, score));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (normalizedScore / 100) * circumference;

  let color = "var(--pass-color)";
  let statusText = "Optimal";
  if (normalizedScore < 50) {
    color = "var(--crit-color)";
    statusText = "Critical Risk";
  } else if (normalizedScore < 70) {
    color = "var(--high-color)";
    statusText = "Action Required";
  } else if (normalizedScore < 85) {
    color = "var(--med-color)";
    statusText = "Moderate";
  }

  return (
    <div className={`flex items-center gap-4 ${className}`.trim()}>
      <div className="relative shrink-0" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="rotate-[-90deg]">
          {/* Background Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="var(--bg-surface-hover)"
            strokeWidth={strokeWidth}
            fill="none"
          />
          {/* Active Progress */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="none"
            style={{ transition: "stroke-dashoffset 0.8s ease" }}
          />
        </svg>

        {/* Center Score Text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span
            className="text-2xl font-extrabold tracking-tight"
            style={{ color }}
          >
            {normalizedScore}
          </span>
          <span className="text-[10px] text-dim uppercase tracking-wider font-semibold">
            / 100
          </span>
        </div>
      </div>

      {showDetails && (
        <div className="flex flex-col">
          <span className="text-xs font-semibold text-muted uppercase tracking-wider">
            Health Index
          </span>
          <span
            className="text-sm font-bold mt-0.5"
            style={{ color }}
          >
            {statusText}
          </span>
          {trend && (
            <span
              className={`text-xs mt-1 font-medium ${
                trendDirection === "up" ? "trend-up" : "trend-down"
              }`}
            >
              {trendDirection === "up" ? "↑ " : "↓ "}
              {trend}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
