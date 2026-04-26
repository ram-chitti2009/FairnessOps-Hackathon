import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#060d1a",
        surface: "#0d1929",
        border: "#1a2d45",
        "border-subtle": "#0f2035",
        muted: "#1e3350",
        "text-primary": "#e8f0fe",
        "text-secondary": "#7a9cc0",
        "text-muted": "#3d5a7a",
        critical: "#ef4444",
        "critical-bg": "#1c0a0a",
        warning: "#f59e0b",
        "warning-bg": "#1c1200",
        healthy: "#22c55e",
        "healthy-bg": "#051a0e",
        info: "#3b82f6",
        "info-bg": "#051230",
        purple: "#8b5cf6",
        "purple-bg": "#120a2e",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
