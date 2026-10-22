import React from "react";

export interface MetricCardProps {
  label: string;
  value: string | number;
  suffix?: string;
  trend?: string;
  trendDirection?: "up" | "down" | "neutral";
  trendPositive?: boolean;
  subtitle?: string;
  severity?: "critical" | "high" | "medium" | "low" | "passed" | "normal" | "warning";
  icon?: React.ReactNode;
  onClick?: () => void;
  className?: string;
}

export function MetricCard({
  label,
  value,
  suffix,
  trend,
  trendDirection = "neutral",
  trendPositive,
  subtitle,
  severity = "normal",
  icon,
  onClick,
  className = "",
}: MetricCardProps) {
  let valueColor = "var(--text-main)";
  if (severity === "critical") valueColor = "var(--crit-color)";
  else if (severity === "high" || severity === "warning") valueColor = "var(--high-color)";
  else if (severity === "medium") valueColor = "var(--med-color)";
  else if (severity === "passed") valueColor = "var(--pass-color)";

  let trendColorClass = "text-muted";
  if (trendDirection === "up") {
    trendColorClass = trendPositive ? "trend-up" : "trend-down";
  } else if (trendDirection === "down") {
    trendColorClass = trendPositive ? "trend-up" : "trend-down";
  }

  const interactiveClass = onClick ? "card-interactive cursor-pointer" : "";

  return (
    <div
      onClick={onClick}
      className={`metric-card ${interactiveClass} ${className}`.trim()}
    >
      <div className="flex-between">
        <span className="metric-card-label">{label}</span>
        {icon && <span className="text-muted shrink-0">{icon}</span>}
      </div>

      <div className="flex items-baseline gap-1 mt-1">
        <span
          className="metric-card-value"
          style={{ color: valueColor }}
        >
          {value}
        </span>
        {suffix && (
          <span className="text-xs text-muted font-medium">{suffix}</span>
        )}
      </div>

      {(trend || subtitle) && (
        <div className="metric-card-trend flex items-center gap-1.5 flex-wrap">
          {trend && (
            <span className={trendColorClass}>
              {trendDirection === "up" ? "↑ " : trendDirection === "down" ? "↓ " : ""}
              {trend}
            </span>
          )}
          {subtitle && (
            <span className="text-dim text-[11px]">{subtitle}</span>
          )}
        </div>
      )}
    </div>
  );
}
