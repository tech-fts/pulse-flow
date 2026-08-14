"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, LayoutDashboard, Radio } from "lucide-react";
import { useBackendHealth } from "@/hooks/useBackendHealth";

export default function Navigation() {
  const pathname = usePathname();
  const { status } = useBackendHealth();

  const navItems = [
    { href: "/", label: "Overview", icon: LayoutDashboard },
    { href: "/telemetry", label: "Telemetry", icon: Activity },
  ];

  return (
    <nav className="h-16 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-50">
      <div className="flex items-center gap-8">
        <Link href="/" className="flex items-center gap-2 font-bold text-slate-100 text-lg">
          <Radio className="w-5 h-5 text-blue-500 animate-pulse" />
          <span>Pulse Flow</span>
        </Link>

        <div className="flex gap-1">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition ${
                  active
                    ? "bg-slate-800 text-slate-100 font-medium"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{label}</span>
              </Link>
            );
          })}
        </div>
      </div>

      <div className="flex items-center gap-2 text-xs font-mono">
        <span className="text-slate-500">API Status:</span>
        <span
          className={`px-2 py-0.5 rounded-full ${
            status === "ok"
              ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
              : status === "degraded"
              ? "bg-amber-950 text-amber-400 border border-amber-800"
              : "bg-rose-950 text-rose-400 border border-rose-800"
          }`}
        >
          {status.toUpperCase()}
        </span>
      </div>
    </nav>
  );
}
