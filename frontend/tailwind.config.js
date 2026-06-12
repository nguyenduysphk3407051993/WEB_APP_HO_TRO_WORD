/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      colors: {
        // Bảng màu "cà phê sữa" — espresso tối → caramel café sữa → kem trắng.
        // Giữ tên token `gold` để mọi class gold-* tự đổi màu đồng bộ.
        gold: {
          50:  "#f7f2ec",  // kem trắng (chữ sáng nhất)
          100: "#ece3d7",  // foam sữa (chữ thường, đọc như trắng)
          200: "#e0cdb4",  // latte nhạt
          300: "#d4b48a",  // café sữa nhạt (chữ nhấn)
          400: "#c29a6e",  // CÀ PHÊ SỮA — màu nhấn chính
          500: "#a07c52",  // caramel đậm (nền nút)
          600: "#8a7763",  // taupe ấm (chữ phụ, trung tính)
          700: "#6f5d4b",  // taupe mờ (chữ phụ mờ)
          800: "#52453a",  // viền sáng
          900: "#372d24",  // viền tối
          950: "#211a15",  // nền nổi tối
        },
      },
    },
  },
  plugins: [],
};
