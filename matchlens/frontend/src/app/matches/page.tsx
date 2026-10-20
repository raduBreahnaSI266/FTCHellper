import { Suspense } from "react";
import { AppShell } from "@/components/app-shell";
import { MatchesView } from "@/components/matches-view";

export default function MatchesPage() {
  return (
    <AppShell>
      <Suspense fallback={<div className="content"><div className="empty-analysis">Se pregătește biblioteca de meciuri…</div></div>}>
        <MatchesView />
      </Suspense>
    </AppShell>
  );
}