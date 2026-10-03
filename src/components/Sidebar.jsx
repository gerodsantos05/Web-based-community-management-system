import React, { useState } from "react";

const cx = (...parts) => parts.filter(Boolean).join(" ");

/**
 * @typedef {{ key: string, label: string, href: string, icon: React.ReactNode }} MenuItem
 */

/**
 * Sidebar component with compact icon rail collapsed mode.
 * @param {{
 *  isCollapsed: boolean,
 *  onToggle?: () => void,
 *  menuItems: MenuItem[],
 *  activeKey?: string,
 *  className?: string,
 * }} props
 */
export default function Sidebar({
  isCollapsed,
  onToggle,
  menuItems,
  activeKey,
  className = "",
}) {
  const [clickedKey, setClickedKey] = useState(null);

  const handleLinkClick = (key) => {
    setClickedKey(key);
    // Remove animation after completion
    setTimeout(() => setClickedKey(null), 400);
  };

  return (
    <aside
      id="admin-sidebar"
      aria-label="Primary sidebar"
      className={cx(
        "flex h-full flex-col border-r border-brand-100 bg-white",
        "[transition:width_240ms_cubic-bezier(0.4,0,0.2,1)] [will-change:width]",
        isCollapsed ? "w-12" : "w-[280px]",
        className
      )}
    >
      <div
        className={cx(
          "border-b border-brand-100",
          isCollapsed ? "flex h-16 items-center justify-center px-0" : "flex h-20 items-center px-3"
        )}
      >
        <div className={cx("flex items-center", isCollapsed ? "justify-center" : "gap-3")}> 
          <span
            className={cx(
              "inline-flex items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 font-bold text-white",
              isCollapsed ? "h-9 w-9 rounded-md text-sm" : "h-11 w-11 text-base",
              "[transition:transform_300ms_cubic-bezier(0.34,1.56,0.64,1)]"
            )}
            aria-hidden="true"
          >
            HB
          </span>
          {!isCollapsed ? (
            <span
              className={cx(
                "overflow-hidden whitespace-nowrap text-sm font-semibold text-ink-900",
                "[transition:max-width_240ms_ease,opacity_240ms_ease,transform_240ms_ease]",
                "max-w-[160px] translate-x-0 opacity-100"
              )}
            >
              HappYness
            </span>
          ) : null}
        </div>
      </div>

      <nav
        id="admin-sidebar-nav"
        className={cx("flex-1 py-3", isCollapsed ? "px-0" : "px-2")}
        aria-label="Main navigation"
      >
        <ul className={cx("flex flex-col", isCollapsed ? "items-center gap-4" : "gap-2")}> 
          {menuItems.map((item) => {
            const isActive = item.key === activeKey;
            const isClicked = item.key === clickedKey;
            const tooltipId = `tooltip-${item.key}`;

            return (
              <li
                key={item.key}
                className={cx(
                  isCollapsed ? "relative flex w-full justify-center" : "",
                  isCollapsed && item.groupStart ? "mt-4" : ""
                )}
              > 
                <a
                  href={item.href}
                  aria-label={item.label}
                  aria-current={isActive ? "page" : undefined}
                  aria-describedby={isCollapsed ? tooltipId : undefined}
                  onClick={() => handleLinkClick(item.key)}
                  className={cx(
                    "group relative flex text-ink-700",
                    "focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400",
                    "[transition:padding_240ms_ease,background-color_320ms_cubic-bezier(0.4,0,0.2,1),color_180ms_ease]",
                    isClicked && "bg-emerald-50",
                    isCollapsed
                      ? "h-8 w-8 items-center justify-center rounded-md transition-colors duration-150 hover:bg-emerald-50"
                      : "w-full items-center rounded-xl px-2 py-1.5"
                  )}
                >
                  {isCollapsed && isActive ? (
                    <span className="absolute left-0 h-8 w-1.5 rounded-r-md bg-emerald-500 [animation:slide-in_300ms_ease-out_1]" aria-hidden="true" />
                  ) : null}

                  <span
                    className={cx(
                      "inline-flex items-center justify-center rounded-md",
                      "[transition:background-color_320ms_ease,color_240ms_ease,transform_300ms_cubic-bezier(0.34,1.56,0.64,1)]",
                      isClicked && "scale-110",
                      isActive && "scale-105",
                      isCollapsed ? "h-8 w-8" : "mr-3 h-10 w-10",
                      isCollapsed
                        ? (isActive ? "text-emerald-600" : "text-ink-600 group-hover:text-emerald-600")
                        : (isActive ? "bg-emerald-100 text-emerald-700" : "text-ink-600 group-hover:bg-brand-50 group-hover:text-ink-900")
                    )}
                    aria-hidden="true"
                  >
                    {item.icon}
                  </span>

                  {!isCollapsed ? (
                    <span
                      className={cx(
                        "overflow-hidden whitespace-nowrap text-sm font-medium",
                        "[transition:max-width_240ms_ease,opacity_240ms_ease,transform_240ms_ease] [will-change:max-width,opacity,transform]",
                        "max-w-[180px] translate-x-0 opacity-100"
                      )}
                    >
                      {item.label}
                    </span>
                  ) : null}

                  {isCollapsed ? (
                    <span
                      id={tooltipId}
                      role="tooltip"
                      className="pointer-events-none absolute left-full top-1/2 z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded bg-ink-900 px-2 py-1 text-xs text-white opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100"
                    >
                      {item.label}
                    </span>
                  ) : null}
                </a>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className={cx("border-t border-brand-100 p-3", isCollapsed ? "flex justify-center" : "")}> 
        <button
          type="button"
          onClick={onToggle}
          className={cx(
            "inline-flex items-center rounded-lg border border-brand-100 bg-white text-sm text-ink-700",
            "transition-all duration-300 hover:bg-brand-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400",
            "[transform:rotate(var(--toggle-rotation,0deg))]",
            isCollapsed ? "h-10 w-10 justify-center" : "h-10 w-full justify-center"
          )}
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-expanded={!isCollapsed}
          aria-controls="admin-sidebar-nav"
        >
          <svg
            className={cx(
              "h-4 w-4 transition-transform duration-300",
              isCollapsed ? "rotate-180" : ""
            )}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="m9 6 6 6-6 6" />
          </svg>
        </button>
      </div>

      <style>{`
        @keyframes slide-in {
          from {
            opacity: 0;
            transform: scaleY(0);
          }
          to {
            opacity: 1;
            transform: scaleY(1);
          }
        }
      `}</style>
    </aside>
  );
}
