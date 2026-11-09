import {
  Component,
  Suspense,
  lazy,
  type ReactNode,
  type ErrorInfo,
} from "react";
import { Routes, Route,  } from "react-router-dom";
import { Layout } from "../components/Layout";
import { Catalog } from "../features/catalog/Catalog";
import { HomePage } from "../pages/HomePage";
import { ContentPage, ContactsPage, NotFound } from "../pages/ContentPage";
import { PageSkeleton } from "../components/Skeleton";
import { cx } from "../components/ui";
const ProductPage = lazy(() =>
  import("../pages/ProductPage").then((m) => ({ default: m.ProductPage })),
);
const CheckoutPage = lazy(() =>
  import("../pages/CheckoutPage").then((m) => ({ default: m.CheckoutPage })),
);
const OrderPage = lazy(() =>
  import("../pages/OrderPage").then((m) => ({ default: m.OrderPage })),
);
export class ErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(_error: Error, _info: ErrorInfo) {}
  render() {
    return this.state.failed ? (
      <section className={cx("content-page")}>
        <h1>Не удалось открыть страницу.</h1>
        <p>Обновите страницу, чтобы повторить загрузку.</p>
        <button
          className={cx("primary-btn")}
          onClick={() => window.location.reload()}
        >
          Обновить
        </button>
      </section>
    ) : (
      this.props.children
    );
  }
}
export function App() {
  return (
    <Layout>
      <Suspense
        fallback={
          <div className={cx("content-page", "shell")}>
            <PageSkeleton />
          </div>
        }
      >
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/catalog" element={<Catalog />} />
          <Route path="/product/:slug" element={<ProductPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/order/:token" element={<OrderPage />} />
          <Route path="/payment/:token" element={<OrderPage localPayment />} />
          <Route path="/delivery" element={<ContentPage page="delivery" />} />
          <Route path="/contacts" element={<ContactsPage />} />
          <Route path="/documents/:slug" element={<ContentPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
    </Layout>
  );
}
