import type { ReactNode } from "react";
import { RunList } from "./RunList";
import { LaunchForm } from "./LaunchForm";

interface Props {
  children: ReactNode;
}

export function Layout({ children }: Props) {
  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>Deliberation</h1>
        <LaunchForm />
        <RunList />
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}
