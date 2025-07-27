/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        'chat': {
          'bg': '#0f0f23',
          'surface': '#1a1a2e',
          'border': '#333366',
          'text': '#e6e6ff',
          'text-muted': '#9999cc',
          'user': '#4f46e5',
          'assistant': '#059669',
          'error': '#dc2626'
        }
      },
      fontFamily: {
        'mono': ['JetBrains Mono', 'Monaco', 'Cascadia Code', 'Roboto Mono', 'monospace']
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography')
  ],
}