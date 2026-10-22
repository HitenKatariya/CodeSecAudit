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

export function SeverityBadge({ severity }: { severity: Severity | string }) {
  const norm = severity.toLowerCase();
  let badgeClass: BadgeVariant = "low";
  let icon = "🔵";

  if (norm === "critical") {
    badgeClass = "critical";
    icon = "🔴";
  } else if (norm === "high") {
    badgeClass = "high";
    icon = "🟠";
  } else if (norm === "medium") {
    badgeClass = "medium";
    icon = "🟡";
  }

  return (
    <Badge variant={badgeClass} icon={icon}>
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
      <Badge variant="blocked" icon="🔴">
        {text || "BLOCKED"}
      </Badge>
    );
  }
  if (norm === "PASSED" || norm === "APPROVE") {
    return (
      <Badge variant="passed" icon="🟢">
        {text || "PASSED"}
      </Badge>
    );
  }
  return (
    <Badge variant="in_review" icon="⏳">
      {text || "IN REVIEW"}
    </Badge>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const norm = status.toLowerCase();
  if (norm === "blocked" || norm === "open") {
    return (
      <Badge variant="blocked" icon="🔴">
        {status.toUpperCase()}
      </Badge>
    );
  }
  if (norm === "protected" || norm === "passed" || norm === "resolved") {
    return (
      <Badge variant="passed" icon="🟢">
        {status.toUpperCase()}
      </Badge>
    );
  }
  if (norm === "warning") {
    return (
      <Badge variant="warning" icon="🟠">
        {status.toUpperCase()}
      </Badge>
    );
  }
  return (
    <Badge variant="low" icon="⚪">
      {status.toUpperCase()}
    </Badge>
  );
}
