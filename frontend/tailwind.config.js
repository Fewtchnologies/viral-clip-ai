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
          dark: '#0B0F17',
          card: '#131A26',
          border: '#222E42',
          yellow: '#FFE600',
          green: '#00FF66',
          cyan: '#00E5FF',
          purple: '#8B5CF6',
        }
      }
    },
  },
  plugins: [],
}
