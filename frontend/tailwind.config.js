/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        slate: {
          950: '#090d16', // 조금 더 은은하고 세련된 핀테크 감성 슬레이트 블랙 배경
        }
      }
    },
  },
  plugins: [],
}
