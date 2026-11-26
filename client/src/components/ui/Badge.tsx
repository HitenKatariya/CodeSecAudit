import React from "react";
import { Severity, GateStatus } from "@/types";

export type BadgeVariant =
  | "critical"
  | "high"
  | "medium"
  | "low"
  | "passed"
  | "blocked"
  | "in_review"
  | "warning"
  | "protected"
  | "open"
  | "resolved";

export interface BadgeProps {
  variant?: BadgeVariant;
  icon?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export function Badge({
  variant = "low",
  icon,
  children,
  className = "",
}: BadgeProps) {
  return (
    <span className={`badge badge-${variant} ${className}`.trim()}>
      {icon && <span className="inline-flex shrink-0">{icon}</span>}
      <span>{children}</span>
    </span>
  );
}

export function StatusDot({ color = "currentColor", size = 7 }: { color?: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 8 8" fill={color} className="inline-block shrink-0 mr-1.5" aria-hidden="true">
      <circle cx="4" cy="4" r="3.5" />
    </svg>
  );
}

export function SeverityBadge({ severity }: { severity: Severity | string }) {
  const norm = severity.toLowerCase();
  let badgeClass: BadgeVariant = "low";
  let dotColor = "var(--info, #3b82f6)";

  if (norm === "critical") {
    badgeClass = "critical";
    dotColor = "var(--crit-color, #ef4444)";
  } else if (norm === "high") {
    badgeClass = "high";
    dotColor = "var(--high-color, #f97316)";
  } else if (norm === "medium") {
    badgeClass = "medium";
    dotColor = "var(--med-color, #eab308)";
  }

  return (
    <Badge variant={badgeClass} icon={<StatusDot color={dotColor} />}>
      {severity.toUpperCase()}
    </Badge>
  );
}

export function GateBadge({
  status,
  text,
}: {
  status: GateStatus | string;
  text?: string;
}) {
  const norm = status.toUpperCase();
  if (norm === "BLOCKED" || norm === "REQUEST_CHANGES") {
    return (
      <Badge variant="blocked" icon={<StatusDot color="var(--crit-color, #ef4444)" />}>
        {text || "BLOCKED"}
      </Badge>
    );
  }
  if (norm === "PASSED" || norm === "APPROVE") {
    return (
      <Badge variant="passed" icon={<StatusDot color="var(--pass-color, #10b981)" />}>
        {text || "PASSED"}
      </Badge>
    );
  }
  return (
    <Badge variant="in_review" icon={<StatusDot color="var(--text-dim, #94a3b8)" />}>
      {text || "IN REVIEW"}
    </Badge>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const norm = status.toLowerCase();
  if (norm === "blocked" || norm === "open") {
    return (
      <Badge variant="blocked" icon={<StatusDot color="var(--crit-color, #ef4444)" />}>
        {status.toUpperCase()}
      </Badge>
    );
  }
  if (norm === "protected" || norm === "passed" || norm === "resolved") {
    return (
      <Badge variant="passed" icon={<StatusDot color="var(--pass-color, #10b981)" />}>
        {status.toUpperCase()}
      </Badge>
    );
  }
  if (norm === "warning") {
    return (
      <Badge variant="warning" icon={<StatusDot color="var(--high-color, #f97316)" />}>
        {status.toUpperCase()}
      </Badge>
    );
  }
  return (
    <Badge variant="low" icon={<StatusDot color="var(--text-dim, #94a3b8)" />}>
      {status.toUpperCase()}
    </Badge>
  );
}
