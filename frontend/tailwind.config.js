/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Fraunces"', "ui-serif", "Georgia", "serif"],
        sans: ['"Inter"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        // warm paper + oxblood + amber, adapted from the Senti reference
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
        ember: {
          DEFAULT: "#e4913f",
          soft: "#f7e6d2",
          ink: "#7a3d10",
        },
        easy: "#3f7d5a",
        medium: "#c9862f",
        hard: "#b0433f",
      },
      letterSpacing: {
        label: "0.18em",
      },
      boxShadow: {
        card: "0 1px 2px rgba(43, 28, 30, 0.04), 0 12px 32px rgba(43, 28, 30, 0.06)",
      },
      backgroundImage: {
        "wine-fade":
          "linear-gradient(180deg, #b07c83 0%, #7c3444 42%, #45182a 78%, #2f1120 100%)",
      },
    },
  },
  plugins: [],
};
