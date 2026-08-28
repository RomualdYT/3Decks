import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/inter";
import { App } from "./app/App";
import "./styles/globals.css";

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
