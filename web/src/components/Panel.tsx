import type { ReactNode } from "react";

export function Panel({
  title,
  meta,
  children,
  flush = false,
  action,
}: {
  title: string;
  meta?: string;
  children: ReactNode;
  flush?: boolean;
  action?: ReactNode;
}) {
  return (
    <div className="panel">
      <div className="panel-head">
        <span className="title">{title}</span>
        <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {meta && <span className="meta">{meta}</span>}
          {action}
        </span>
      </div>
      <div className={"panel-body" + (flush ? " flush" : "")}>{children}</div>
    </div>
  );
}
