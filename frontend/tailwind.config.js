/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ground: "#E9EDF1",
        surface: "#FFFFFF",
        sunken: "#F3F5F8",
        ink: "#12171E",
        muted: "#59636E",
        line: "#D2D9E0",
        cobalt: "#2348C8",
        risk: {
          low: "#1E7A66",
          med: "#B5791A",
          high: "#B23322",
          standard: "#59636E",
        },
      },
      fontFamily: {
        display: ['"IBM Plex Sans Condensed"', "system-ui", "sans-serif"],
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
      letterSpacing: {
        label: "0.14em",
      },
      boxShadow: {
        panel: "0 1px 2px 0 rgba(18,23,30,0.05)",
      },
    },
  },
  plugins: [],
}
