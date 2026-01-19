"use client";

import Link from "next/link";

const navItems = [
  { label: "Dashboard", href: "/" },
  { label: "Mentions", href: "/#mentions" },
  { label: "Keywords", href: "/#keywords" },
];

export function Sidebar() {
  return (
    <aside className="flex h-full w-64 flex-col border-r border-slate-800 bg-slate-950 px-4 py-6">
      <div className="mb-8">
        <h1 className="text-xl font-semibold text-slate-100">
          Open Mentions
        </h1>
        <p className="text-sm text-slate-400">Analytics Dashboard</p>
      </div>
      <nav className="space-y-2">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="block rounded-md px-3 py-2 text-sm text-slate-200 hover:bg-slate-900"
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="mt-auto text-xs text-slate-500">
        Powered by FastAPI + Tremor
      </div>
    </aside>
  );
}
