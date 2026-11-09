import { renderToString } from "react-dom/server";
import { StaticRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Catalog } from "./features/catalog/Catalog";
import { HomePage } from "./pages/HomePage";
import { ProductPage } from "./pages/ProductPage";
import { ContentPage, ContactsPage, NotFound } from "./pages/ContentPage";
import { StoreProvider } from "./app/StoreContext";
import { CartProvider } from "./features/cart/CartContext";
import { PublicDataProvider, type PublicData } from "./app/PublicData";
export function render(url: string, data: PublicData) {
  return renderToString(
    <StaticRouter location={url}>
      <PublicDataProvider data={data}>
        <StoreProvider>
          <CartProvider>
            <Layout>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/catalog" element={<Catalog />} />
                <Route path="/product/:slug" element={<ProductPage />} />
                <Route
                  path="/delivery"
                  element={<ContentPage page="delivery" />}
                />
                <Route path="/contacts" element={<ContactsPage />} />
                <Route path="/documents/:slug" element={<ContentPage />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </Layout>
          </CartProvider>
        </StoreProvider>
      </PublicDataProvider>
    </StaticRouter>,
  );
}
