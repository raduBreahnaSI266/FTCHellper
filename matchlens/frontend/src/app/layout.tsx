import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MatchLens | FTC Match Analysis",
  description: "Evidence-first FTC match video analysis workspace.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}