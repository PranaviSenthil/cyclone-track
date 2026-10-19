/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cyclo: {
          darkest: '#050811',
          dark: '#0A101F',
          card: '#0F182E',
          cardBorder: '#1E2D4A',
          muted: '#8A99AD',
          cyan: '#00E5FF',
          cyanHover: '#33EBFF',
          blue: '#1A73E8',
          electric: '#0066FF',
          accent: '#38BDF8',
          danger: '#FF3366',
          warning: '#FFAA00',
          success: '#00E676'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace']
      },
      boxShadow: {
        glow: '0 0 25px -5px rgba(0, 229, 255, 0.25)',
        glowBlue: '0 0 30px -5px rgba(26, 115, 232, 0.3)',
        card: '0 8px 32px 0 rgba(0, 0, 0, 0.45)'
      }
    },
  },
  plugins: [],
}
