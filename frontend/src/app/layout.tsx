import type { Metadata } from "next";
import "./globals.css";
import Navigation from "@/components/Navigation";

export const metadata: Metadata = {
  title: "Pulse Flow — Telemetry Dashboard",
  description: "Real-time SSE event ingestion and telemetry streaming platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 antialiased min-h-screen flex flex-col">
        <Navigation />
        <div className="flex-1">{children}</div>
      </body>
    </html>
  );
}
