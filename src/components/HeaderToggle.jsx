import React from "react";

/**
 * @param {{ isCollapsed: boolean, onToggle: () => void, className?: string }} props
 */
export default function HeaderToggle({ isCollapsed, onToggle, className = "" }) {
  return (
    <button
      type="button"
      aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
      aria-expanded={!isCollapsed}
      aria-controls="admin-sidebar"
      onClick={onToggle}
      className={[
        "inline-flex h-10 w-10 items-center justify-center rounded-lg border border-brand-100 bg-white text-ink-700",
        "transition-colors duration-200 hover:bg-brand-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400",
        className,
      ].join(" ")}
    >
      <svg
        className="h-5 w-5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        aria-hidden="true"
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 7h16M4 12h16M4 17h16" />
      </svg>
    </button>
  );
}
