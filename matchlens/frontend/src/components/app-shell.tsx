"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, ClipboardList, FileText, Flag, FolderKanban, Settings, Users, Video } from "lucide-react";

const navigation = [
  { label: "Overview", href: "/", icon: BarChart3 },
  { label: "Matches", href: "/matches", icon: ClipboardList },
  { label: "Analyze Video", href: "/#analysis", icon: Video },
  { label: "Teams", href: "#", icon: Users },
  { label: "Reports", href: "#", icon: FileText },
  { label: "Settings", href: "#", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="shell">
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="MatchLens overview">
          <span className="brand-mark">ML</span><span>MatchLens</span>
        </Link>
        <div className="workspace-label">Workspace</div>
        <nav className="nav" aria-label="Main navigation">
          {navigation.map(({ label, href, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : href === "/matches" && pathname.startsWith("/matches");
            return (
              <Link className={active ? "active" : ""} href={href} key={label} aria-current={active ? "page" : undefined}>
                <Icon aria-hidden="true" />{label}
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-foot"><FolderKanban size={15} /> Local workspace<br />No team account connected</div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="crumb"><Flag size={15} /> FTC / Workspace</div>
          <span className="local-pill">LOCAL ONLY</span>
        </header>
        {children}
      </main>
    </div>
  );
}