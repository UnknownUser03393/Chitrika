import { createRoot } from "react-dom/client";
import { MotionConfig } from "motion/react";
import App from "./app/App.tsx";
import "./styles/index.css";

// Browser tab vs Electron window title
document.title = window.desktopAPI ? "Chitrika Desktop" : "Chitrika Web";

createRoot(document.getElementById("root")!).render(
  <MotionConfig reducedMotion="user">
    <App />
  </MotionConfig>
);
  