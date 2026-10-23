import React from "react";

export interface PageHeaderProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  subtitle,
  badge,
  actions,
  className = "",
}: PageHeaderProps) {
  return (
    <div className={`page-header ${className}`.trim()}>
      <div style={{ minWidth: 0, flex: "1 1 auto" }}>
        <div className="flex items-center gap-2.5 flex-wrap">
          <h1 className="page-title">{title}</h1>
          {badge && <div className="inline-flex shrink-0">{badge}</div>}
        </div>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>

      {actions && <div className="page-header-actions shrink-0">{actions}</div>}
    </div>
  );
}
