import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App, ErrorBoundary } from "./app/App";
import { StoreProvider } from "./app/StoreContext";
import { CartProvider } from "./features/cart/CartContext";
import { PublicDataProvider, type PublicData } from "./app/PublicData";
import "./styles/global.scss";
const preloaded: PublicData = JSON.parse(
  document.getElementById("public-data")?.textContent ?? "{}",
);
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <PublicDataProvider data={preloaded}>
          <StoreProvider>
            <CartProvider>
              <App />
            </CartProvider>
          </StoreProvider>
        </PublicDataProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
);
