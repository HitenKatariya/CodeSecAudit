"use client";

import React, { useEffect, useState } from "react";
import { SunIcon, MoonIcon } from "../ui/Icons";

export function ThemeToggle({ className = "" }: { className?: string }) {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const saved = localStorage.getItem("codesec_theme") as "dark" | "light" | null;
    if (saved === "light" || saved === "dark") {
      setTheme(saved);
      document.documentElement.setAttribute("data-theme", saved);
    } else {
      document.documentElement.setAttribute("data-theme", "dark");
    }
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    localStorage.setItem("codesec_theme", nextTheme);
    document.documentElement.setAttribute("data-theme", nextTheme);
  };

  if (!mounted) {
    return (
      <button
        type="button"
        className={`theme-toggle-btn ${className}`}
        aria-label="Toggle White/Black UI"
      >
        <span className="w-4 h-4 opacity-0" />
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={`theme-toggle-btn ${className}`}
      title={theme === "dark" ? "Switch to White UI" : "Switch to Black UI"}
      aria-label="Toggle White/Black UI theme"
    >
      {theme === "dark" ? (
        <>
          <SunIcon size={14} className="theme-toggle-icon" />
          <span className="theme-toggle-label">White UI</span>
        </>
      ) : (
        <>
          <MoonIcon size={14} className="theme-toggle-icon" />
          <span className="theme-toggle-label">Black UI</span>
        </>
      )}
    </button>
  );
}
