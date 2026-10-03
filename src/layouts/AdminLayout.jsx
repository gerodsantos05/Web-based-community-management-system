import React from "react";
import HeaderToggle from "../components/HeaderToggle";
import Sidebar from "../components/Sidebar";
import { useSidebar } from "../components/useSidebar";

const MENU_ITEMS = [
  {
    key: "dashboard",
    label: "Dashboard",
    href: "/admin",
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
        <path d="M3 13h8V3H3v10zM13 21h8V11h-8v10zM13 3v6h8V3h-8zM3 21h8v-8H3v8z" />
      </svg>
    ),
  },
  {
    key: "inventory",
    label: "Inventory",
    href: "/admin/inventory",
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
        <path d="M3 7l9-4 9 4M3 7v10l9 5 9-5V7" />
      </svg>
    ),
  },
  {
    key: "reports",
    groupStart: true,
    label: "Reports",
    href: "/admin/reports",
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
        <path d="M4 19h16M7 15V9m5 6V5m5 10v-4" />
      </svg>
    ),
  },
  {
    key: "settings",
    groupStart: true,
    label: "Settings",
    href: "/admin/settings",
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.2a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3h.1A1.7 1.7 0 0 0 10 3.2V3a2 2 0 1 1 4 0v.2a1.7 1.7 0 0 0 1 1.5h.1a1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8v.1a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.2a1.7 1.7 0 0 0-1.5 1z" />
      </svg>
    ),
  },
];

/**
 * Demo integration layout for Sidebar + resizable main content.
 * @param {{ children?: React.ReactNode, activeKey?: string }} props
 */
export default function AdminLayout({ children, activeKey = "inventory" }) {
  const { isCollapsed, toggle } = useSidebar({
    key: "admin:sidebar:collapsed",
    initial: false,
    persist: true,
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="grid min-h-screen [grid-template-columns:auto_1fr]">
        <Sidebar
          isCollapsed={isCollapsed}
          onToggle={toggle}
          menuItems={MENU_ITEMS}
          activeKey={activeKey}
        />

        <div className="flex min-w-0 flex-col">
          <header className="sticky top-0 z-30 flex h-20 items-center justify-between border-b border-brand-100 bg-white/95 px-4 backdrop-blur-sm md:px-6">
            <div className="flex items-center gap-3">
              <HeaderToggle isCollapsed={isCollapsed} onToggle={toggle} />
              <h1 className="text-base font-semibold text-ink-900 md:text-lg">Admin Workspace</h1>
            </div>
            <div className="text-sm text-ink-500">Responsive content region</div>
          </header>

          <main className="min-w-0 flex-1 p-4 md:p-6 lg:p-8">
            {children || (
              <section className="rounded-2xl border border-brand-100 bg-white p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-ink-900">Main Content</h2>
                <p className="mt-2 text-sm text-ink-600">
                  Toggle the sidebar from the header button and verify the content area expands/collapses without overlap.
                </p>
              </section>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
