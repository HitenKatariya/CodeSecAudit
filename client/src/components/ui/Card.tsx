import React from "react";

export interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
  title?: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  footer?: React.ReactNode;
  interactive?: boolean;
  className?: string;
  children?: React.ReactNode;
}

export function Card({
  title,
  description,
  actions,
  footer,
  interactive = false,
  className = "",
  children,
  ...props
}: CardProps) {
  const hasHeader = title || description || actions;
  const interactiveClass = interactive ? "card-interactive" : "";

  return (
    <div
      className={`card ${interactiveClass} ${className}`.trim()}
      {...props}
    >
      {hasHeader && (
        <div className="flex-between mb-4 pb-2 border-b border-subtle">
          <div>
            {title && (
              <h3 className="text-sm font-semibold text-main tracking-tight">
                {title}
              </h3>
            )}
            {description && (
              <p className="text-xs text-muted mt-0.5">{description}</p>
            )}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}

      <div>{children}</div>

      {footer && (
        <div className="mt-4 pt-3 border-t border-subtle text-xs text-muted flex-between">
          {footer}
        </div>
      )}
    </div>
  );
}
