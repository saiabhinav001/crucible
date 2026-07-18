import "@crucible/ui/tokens.css";

import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppShell } from "./shell";

export const metadata: Metadata = {
  title: "Crucible",
  description: "Evaluation and reliability platform for LLM agents",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
