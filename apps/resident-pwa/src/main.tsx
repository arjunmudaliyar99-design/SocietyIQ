import "@societyiq/shared/fonts";
import "./index.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { SettingsProvider } from "@societyiq/shared";

import { Root } from "./Root";

const root = document.getElementById("root");
if (!root) throw new Error("Root element missing");

createRoot(root).render(
  <StrictMode>
    <SettingsProvider>
      <BrowserRouter>
        <Root />
      </BrowserRouter>
    </SettingsProvider>
  </StrictMode>,
);
