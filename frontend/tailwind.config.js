/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: '#101c2b',
          accent: '#f08a3c',
          muted: '#778392',
        },
        industrial: {
          navy: '#101c2b',
          charcoal: '#253243',
          steel: '#778392',
          orange: '#f08a3c',
        },
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'Arial', 'sans-serif'],
        mono: ['Consolas', 'monospace'],
      }
    },
  },
  plugins: [],
}
