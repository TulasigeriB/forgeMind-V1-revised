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
          dark: '#1a1a1a',
          accent: '#3b82f6',
          muted: '#6b7280',
        }
      }
    },
  },
  plugins: [],
}
