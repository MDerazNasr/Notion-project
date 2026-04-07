import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "var(--ink)",
        faint: "var(--faint)",
        surface: "var(--surface)",
        line: "var(--line)",
        accent: "var(--accent)",
        redSoft: "var(--red-soft)",
        amberSoft: "var(--amber-soft)",
        greenSoft: "var(--green-soft)"
      },
      borderRadius: {
        notion: "6px",
        subtle: "3px"
      },
      boxShadow: {
        card: "0 12px 40px rgba(55, 53, 47, 0.04)"
      }
    }
  },
  plugins: []
};

export default config;
