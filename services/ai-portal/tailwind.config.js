/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'eggshell': '#f9f6f2',
        'ochre': '#cc7722',
        'rjlf-blue': '#005a87',
        'rjlf-gold': '#b8956a',
        'rjlf-gold-dark': '#9b7d55',
        'dark': {
          900: '#0a0a0f',
          800: '#12121a',
          700: '#1a1a24',
          600: '#22222e',
        },
        'accent': {
          blue: '#00d4ff',
          'royal-blue': '#4169e1',
          'denim-blue': '#1560BD',
          purple: '#8b5cf6',
          gold: '#fbbf24',
          'soft-gold': '#d4af37',
        }
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
      },
      animation: {
        'gradient': 'gradient 8s linear infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'float': 'float 6s ease-in-out infinite',
      }
    },
  },
  plugins: [],
}