/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary:   '#0d1117',
        secondary: '#161b22',
        tertiary:  '#21262d',
        // Category accents
        home:      '#00d4ff',
        work:      '#34d399',
        data:      '#60a5fa',
        analytics: '#fbbf24',
        learn:     '#a78bfa',
        // Semantic
        accent:    '#00d4ff',
        success:   '#34d399',
        warning:   '#fbbf24',
        danger:    '#f87171',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Cascadia Code', 'monospace'],
      },
      animation: {
        'fade-in':  'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.25s ease-out',
      },
      keyframes: {
        fadeIn:  { from: { opacity: '0' }, to: { opacity: '1' } },
        slideUp: { from: { opacity: '0', transform: 'translateY(8px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
}
