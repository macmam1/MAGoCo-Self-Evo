/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        /* Theme-driven tokens (see src/index.css [data-theme=...]).
           These classes already exist across components (bg-bg-0, text-text-0...). */
        bg: {
          0: "var(--bg-0)",
          1: "var(--bg-1)",
          2: "var(--bg-2)",
        },
        text: {
          0: "var(--text-0)",
          1: "var(--text-1)",
          2: "var(--text-2)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          2: "var(--accent-2)",
          3: "var(--accent-3)",
        },
        primary: {
          50: "#f0f9ff",
          100: "#e0f2fe",
          500: "#0ea5e9",
          600: "#0284c7",
          700: "#0369a1",
          900: "#0c4a6e",
        },
      },
      fontFamily: {
        sans: ["var(--font-body)", "Vazirmatn", "Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
