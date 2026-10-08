/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          darkest: '#060B12',
          darker: '#08111C',
          dark: '#0B1420',
          border: '#1A2332',
          accent: '#00F0FF',
          accentGlow: 'rgba(0, 240, 255, 0.2)',
          text: '#8BA1B6',
          textBright: '#E2E8F0',
        },
        risk: {
          critical: '#FF2A2A',
          high: '#FF7B00',
          medium: '#FFB800',
          low: '#00A3FF',
          info: '#8BA1B6'
        }
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      animation: {
        'radar-spin': 'radar 4s linear infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        radar: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        }
      }
    },
  },
  plugins: [],
}
