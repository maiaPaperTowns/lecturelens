/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Space Grotesk"', "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ['"Inter"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        paper: "#f4efe7",
        card: "#fbf8f2",
        line: "#e4dccd",
        ink: {
          DEFAULT: "#2b1c1e",
          soft: "#6b5a56",
          faint: "#9a8c84",
        },
        wine: {
          DEFAULT: "#5a2231",
          deep: "#3d1622",
          soft: "#8a4a58",
        },
        rose: "#b07c83",
        // accent: a deep berry / plum, replaces the old amber
        accent: {
          DEFAULT: "#7c2e49",
          soft: "#efe3e8",
          ink: "#5a2231",
        },
        easy: "#3f7d5a",
        medium: "#b98038",
        hard: "#b0433f",
      },
      letterSpacing: {
        label: "0.18em",
      },
      boxShadow: {
        card: "0 1px 2px rgba(43, 28, 30, 0.04), 0 12px 32px rgba(43, 28, 30, 0.06)",
        glass: "inset 0 1px 0 rgba(255,255,255,0.55), 0 8px 30px rgba(43,28,30,0.10)",
        "glass-dark":
          "inset 0 1px 0 rgba(255,255,255,0.18), 0 10px 30px rgba(43,28,30,0.28)",
      },
      backdropBlur: {
        xs: "2px",
      },
      backgroundImage: {
        "wine-fade":
          "linear-gradient(180deg, #b07c83 0%, #7c3444 42%, #45182a 78%, #2f1120 100%)",
      },
    },
  },
  plugins: [],
};
