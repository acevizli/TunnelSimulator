/// <reference types="vite/client" />
import { createRoot } from "react-dom/client";
import App from "./App";
import ReplayPrototype from "./prototype/ReplayPrototype";
import "./styles.css";

// PROTOTYPE (replay layout): the dev server shows the layout variants; a build shows only the real page
createRoot(document.getElementById("root")!).render(import.meta.env.DEV ? <ReplayPrototype /> : <App />);
