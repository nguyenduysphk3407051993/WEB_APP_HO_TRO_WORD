/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      colors: {
        gold: {
          50:  "#fef6d0",
          100: "#fce99a",
          200: "#f5d870",
          300: "#e8c848",
          400: "#d4a830",
          500: "#b89030",
          600: "#8d7028",
          700: "#6b5520",
          800: "#4a3c18",
          900: "#2e2610",
          950: "#1a1504",
        },
      },
    },
  },
  plugins: [],
};
