import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          900: "#0b132b",
          800: "#1c2541",
          700: "#1e3a8a",
          600: "#2563eb",
        },
        reconciled: {
          light: "#dcfce7",
          border: "#86efac",
          DEFAULT: "#10b981",
          dark: "#047857",
        },
        pending: {
          light: "#fef9c3",
          border: "#fde047",
          DEFAULT: "#f59e0b",
          dark: "#b45309",
        },
        divergent: {
          light: "#fee2e2",
          border: "#fca5a5",
          DEFAULT: "#ef4444",
          dark: "#b91c1c",
        }
      },
    },
  },
  plugins: [],
};
export default config;
