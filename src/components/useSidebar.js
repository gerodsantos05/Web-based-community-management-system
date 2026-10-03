import { useCallback, useEffect, useState } from "react";

/**
 * useSidebar manages collapsed/expanded sidebar state with optional persistence.
 * @param {{ key?: string, initial?: boolean, persist?: boolean }} [options]
 */
export function useSidebar({
  key = "admin:sidebar:collapsed",
  initial = false,
  persist = true,
} = {}) {
  const [isCollapsed, setCollapsed] = useState(() => {
    if (!persist || typeof window === "undefined") {
      return initial;
    }

    try {
      const raw = window.localStorage.getItem(key);
      if (raw === null) {
        return initial;
      }
      return JSON.parse(raw) === true;
    } catch (error) {
      return initial;
    }
  });

  useEffect(() => {
    if (!persist || typeof window === "undefined") {
      return;
    }

    try {
      window.localStorage.setItem(key, JSON.stringify(isCollapsed));
    } catch (error) {
      // Ignore storage errors (private mode/quota) and keep UI responsive.
    }
  }, [isCollapsed, key, persist]);

  const toggle = useCallback(() => {
    setCollapsed((value) => !value);
  }, []);

  return {
    isCollapsed,
    toggle,
    setCollapsed,
  };
}
