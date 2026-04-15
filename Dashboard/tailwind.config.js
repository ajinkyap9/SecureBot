/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Sora', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'ui-monospace', 'monospace'],
      },
      colors: {
        command: {
          950: '#050b17',
          900: '#081227',
          800: '#0d1f3e',
          700: '#11305f',
          600: '#164987',
          500: '#1e6cc0',
        },
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(82, 148, 255, 0.2), 0 24px 48px -24px rgba(3, 17, 44, 0.8)',
      },
      keyframes: {
        rise: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '0.65' },
          '50%': { opacity: '1' },
        },
      },
      animation: {
        rise: 'rise 0.45s ease-out both',
        pulseSoft: 'pulseSoft 2.2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}

