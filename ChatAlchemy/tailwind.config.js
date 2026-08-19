/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        'gray-750': '#2D3748',
      },
      typography: {
        DEFAULT: { css: { maxWidth: 'none', color: 'inherit', p: { color: 'inherit' } } },
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
};
