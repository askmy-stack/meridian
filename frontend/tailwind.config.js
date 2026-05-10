/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Custom risk colors
        risk: {
          none: '#10b981',
          low: '#3b82f6',
          medium: '#f59e0b',
          high: '#f97316',
          critical: '#ef4444'
        }
      }
    },
  },
  plugins: [],
}
