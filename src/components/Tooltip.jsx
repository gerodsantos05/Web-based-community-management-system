import React from "react";

/**
 * Lightweight tooltip that becomes visible on parent .group hover/focus-within.
 * @param {{ id: string, children: React.ReactNode, side?: "right" | "left" }} props
 */
export function Tooltip({ id, children, side = "right" }) {
  const sideClass = side === "left" ? "right-full mr-2" : "left-full ml-2";

  return (
    <span
      id={id}
      role="tooltip"
      className={[
        "pointer-events-none absolute top-1/2 z-50 -translate-y-1/2 whitespace-nowrap rounded-md bg-slate-900 px-2 py-1 text-xs text-white",
        "opacity-0 translate-x-1 scale-95 transition-all duration-150",
        "group-hover:opacity-100 group-hover:translate-x-0 group-hover:scale-100",
        "group-focus-within:opacity-100 group-focus-within:translate-x-0 group-focus-within:scale-100",
        "group-focus-visible:opacity-100 group-focus-visible:translate-x-0 group-focus-visible:scale-100",
        sideClass,
      ].join(" ")}
    >
      {children}
    </span>
  );
}
