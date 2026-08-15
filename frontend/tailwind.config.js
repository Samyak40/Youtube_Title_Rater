/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0F0F0F',
        surface: '#272727',
        primary: '#FF0000',
        accent: '#CC0000',
        textPrimary: '#F1F1F1',
        textSecondary: '#AAAAAA',
        danger: '#FF4E45',
        success: '#2BA640',
      }
    },
  },
  plugins: [],
}
