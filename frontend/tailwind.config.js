/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        twitter: '#1DA1F2',
        xDark: {
          900: '#000000',
          850: '#0c0f14',
          800: '#16181c',
          700: '#202327',
          600: '#2f3336',
          500: '#71767b',
        }
      }
    },
  },
  plugins: [],
};
