import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FairnessOps — Clinical AI Monitoring",
  description: "Real-time fairness monitoring for clinical AI systems",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
