/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        fleet: {
          900: "#0b0b0f", 800: "#1b1b21", 700: "#2f2f38",
          600: "#4a4a56", 500: "#9a9aa6", 400: "#c2c2cc",
          300: "#d8d8de", 200: "#ececef", 100: "#f4f4f5",
        },
      },
    },
  },
  plugins: [],
};
