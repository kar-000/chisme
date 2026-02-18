/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        crt: {
          bg:        '#1a1612',
          'bg-dark': '#0a0a0a',
          teal:      '#00CED1',
          'teal-lt': '#5DADE2',
          gray:      '#8B8B8B',
          pink:      '#FFB6C1',
          orange:    '#FF8C42',
        },
      },
      fontFamily: {
        mono: ['IBM Plex Mono', 'Courier New', 'monospace'],
      },
      boxShadow: {
        glow:        '0 0 10px rgba(0,206,209,0.6)',
        'glow-sm':   '0 0 6px rgba(0,206,209,0.3)',
        'glow-lg':   '0 0 20px rgba(0,206,209,0.6)',
        'glow-pink': '0 0 6px rgba(255,182,193,0.3)',
      },
    },
  },
  plugins: [],
}
