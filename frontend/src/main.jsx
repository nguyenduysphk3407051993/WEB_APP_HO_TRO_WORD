import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

// ── Gold cursor sparkle (Mệnh Kim) ───────────────────────────────────────────

const GOLD_COLORS = ["#d4a830", "#e8c848", "#f5d870", "#fce99a", "#b89030"];

function createSparkle(x, y) {
  const el = document.createElement("div");
  el.className = "cursor-sparkle";
  const size = 4 + Math.random() * 5;
  const color = GOLD_COLORS[Math.floor(Math.random() * GOLD_COLORS.length)];
  const ox = (Math.random() - 0.5) * 22;
  const oy = (Math.random() - 0.5) * 22;
  // 4-pointed star via clip-path
  el.style.cssText = `left:${x + ox}px;top:${y + oy}px;width:${size}px;height:${size}px;`
    + `background:${color};clip-path:polygon(50% 0%,56% 44%,100% 50%,56% 56%,50% 100%,44% 56%,0% 50%,44% 44%);`;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 560);
}

function initCursor() {
  if (window.matchMedia("(hover: none)").matches) return;

  const dot  = document.createElement("div");
  dot.id     = "cursor-dot";
  const ring = document.createElement("div");
  ring.id    = "cursor-ring";
  document.body.append(dot, ring);

  let mx = 0, my = 0, rx = 0, ry = 0, lastSparkle = 0;

  document.addEventListener("mousemove", (e) => {
    mx = e.clientX;
    my = e.clientY;
    dot.style.left = mx + "px";
    dot.style.top  = my + "px";
    const now = Date.now();
    if (now - lastSparkle > 75) {
      lastSparkle = now;
      createSparkle(mx, my);
    }
  });

  // Smooth lag ring follow
  (function raf() {
    rx += (mx - rx) * 0.13;
    ry += (my - ry) * 0.13;
    ring.style.left = rx + "px";
    ring.style.top  = ry + "px";
    requestAnimationFrame(raf);
  })();

  // Hover states
  document.addEventListener("mouseover", (e) => {
    if (e.target.matches("input,textarea,select")) {
      document.body.classList.add("cursor-text-field");
    } else if (e.target.closest("button,a,[role='button'],select")) {
      document.body.classList.add("cursor-hover");
    }
  });
  document.addEventListener("mouseout", (e) => {
    if (e.target.matches("input,textarea,select")) {
      document.body.classList.remove("cursor-text-field");
    } else if (e.target.closest("button,a,[role='button'],select")) {
      document.body.classList.remove("cursor-hover");
    }
  });

  // Hide when leaving window
  document.addEventListener("mouseleave", () => {
    dot.style.opacity = "0";
    ring.style.opacity = "0";
  });
  document.addEventListener("mouseenter", () => {
    dot.style.opacity = "1";
    ring.style.opacity = "1";
  });
}

initCursor();

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
