import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import StudioWorkspace from "./studio/StudioWorkspace";

createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <StudioWorkspace />
  </React.StrictMode>
);
