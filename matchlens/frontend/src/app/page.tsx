import { UploadWorkspace } from "@/components/upload-workspace";
import { AppShell } from "@/components/app-shell";
import { RecentMatches } from "@/components/recent-matches";
import { Info } from "lucide-react";

export default function Home() {
  return (
    <AppShell>
        <div className="content">
          <section className="heading-row">
            <div>
              <div className="eyebrow">Engineering workspace</div>
              <h1>Match overview</h1>
              <p className="subhead">Inspect match footage, measure video coverage, and mark events for review.</p>
            </div>
            <a className="button" href="#analysis">Analyze a video</a>
          </section>

          <RecentMatches />

          <UploadWorkspace />

          <div className="notice" role="note"><Info aria-hidden="true" />
            <span><strong>Local-only workspace.</strong> Video files and metadata stay on this computer. Robot detection is not configured; the available analysis measures video metadata and sampled frames.</span>
          </div>
        </div>
    </AppShell>
  );
}