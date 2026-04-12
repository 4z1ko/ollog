/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ['./templates/**/*.html'],
  theme: {
    extend: {
      colors: {
        sidebar: {
          DEFAULT: '#1a1d2e',
          hover: '#252941',
          active: '#4338ca',
          border: '#2d3561',
          text: '#c4c9e4',
        },
        canvas: {
          light: '#f2f2f7',
          dark: '#0f0f0f',
        },
        surface: {
          light: '#ffffff',
          dark: '#1c1c1e',
        },
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
      },
    },
  },
  plugins: [],
}
