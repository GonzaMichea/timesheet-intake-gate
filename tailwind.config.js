/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    // Escala tipográfica fija (design §9): 14 · 16 · 20 · 28 · 40 · 64
    fontSize: {
      sm: ["14px", "20px"],
      base: ["16px", "24px"],
      lg: ["20px", "28px"],
      xl: ["28px", "34px"],
      "2xl": ["40px", "44px"],
      display: ["64px", "64px"],
    },
    fontFamily: {
      display: ['"Archivo"', "sans-serif"],
      sans: ['"IBM Plex Sans"', "sans-serif"],
    },
    extend: {
      // Único movimiento orquestado de la app: la cinta de filas se llena de izquierda a derecha
      keyframes: {
        "ribbon-fill": {
          from: { clipPath: "inset(0 100% 0 0)" },
          to: { clipPath: "inset(0 0 0 0)" },
        },
      },
      animation: { ribbon: "ribbon-fill 900ms ease-out both" },
      colors: {
        paper: "#F3F5F4",
        surface: "#FFFFFF",
        ink: "#17212B",
        graphite: "#4B5967",
        line: "#D3DADF",
        stamp: "#1D4ED8",
        // Colores de disposición: siempre acompañados de texto e ícono
        load: "#15803D",
        warn: "#A16207",
        quarantine: "#C2410C",
        block: "#B91C1C",
      },
    },
  },
  plugins: [],
};
