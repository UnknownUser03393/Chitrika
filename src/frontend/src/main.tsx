
  import { createRoot } from "react-dom/client";
  import { MotionConfig } from "motion/react";
  import App from "./app/App.tsx";
  import "./styles/index.css";

  createRoot(document.getElementById("root")!).render(
    <MotionConfig reducedMotion="user">
      <App />
    </MotionConfig>
  );
  