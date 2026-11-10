import { useState, useEffect, useRef, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useStore } from "../app/StoreContext";
import { useCart } from "../features/cart/CartContext";
import { cx, Logo } from "./ui";
import { Skeleton, SiteLoader } from "./Skeleton";
import { usePageMotion } from "../hooks/usePageMotion";
import { CartDrawer } from "../features/cart/CartDrawer";
export function Layout({ children }: { children: ReactNode }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const { data: store } = useStore();
  const cart = useCart();
  const location = useLocation();
  usePageMotion(location.pathname);
  const previousPath = useRef("");
  const navigate = useNavigate();
  const [menu, setMenu] = useState(false),
    [search, setSearch] = useState(false),
    [query, setQuery] = useState("");
  useEffect(() => {
    setMenu(false);
    const pathChanged = previousPath.current !== location.pathname;
    previousPath.current = location.pathname;
    if (location.hash) {
      const timer = setTimeout(
        () =>
          document.getElementById(location.hash.slice(1))?.scrollIntoView({
            behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
              ? "instant"
              : "smooth",
          }),
        80,
      );
      return () => clearTimeout(timer);
    }
    if (pathChanged) window.scrollTo(0, 0);
  }, [location.pathname, location.hash]);
  useEffect(() => {
    if (search) document.getElementById("site-search")?.focus();
  }, [search]);
  const links = (
    <>
      <Link to="/catalog">Каталог</Link>
      <Link to="/catalog?new=1">Новинки</Link>
      <Link to="/#manifesto">О бренде</Link>
      <Link to="/delivery">Доставка</Link>
    </>
  );
  return (
    <div className={cx(mounted && "motion")}>
      <SiteLoader />
      <a className={cx("skip-link")} href="#main">
        Перейти к содержимому
      </a>
      <div className={cx("masthead")} id="top">
        <div className={cx("topline")}>
          {store?.announcement ?? <Skeleton />}
        </div>
        <header className={cx("head", "shell")}>
          <nav className={cx("desktop-nav")} aria-label="Главная навигация">
            {links}
          </nav>
          <button
            className={cx("header-action", "mobile-menu-btn")}
            aria-expanded={menu}
            aria-controls="mobile-nav"
            onClick={() => setMenu((x) => !x)}
          >
            Меню
          </button>
          <Link
            className={cx("brand")}
            to="/"
            aria-label="ATELIER NOIR — на главную"
          >
            <Logo />
          </Link>
          <div className={cx("header-actions")}>
            <button
              className={cx("header-action", "search-label")}
              aria-expanded={search}
              onClick={() => setSearch((x) => !x)}
            >
              Поиск
            </button>
            <button
              className={cx("header-action")}
              onClick={() => cart.setOpen(true)}
              aria-label="Открыть корзину"
            >
              Корзина{" "}
              <span
                key={cart.lines.reduce((sum, x) => sum + x.quantity, 0)}
                className={cx("bag-count")}
              >
                {cart.lines.reduce((sum, x) => sum + x.quantity, 0)}
              </span>
            </button>
          </div>
        </header>
        <nav
          className={cx("mobile-nav")}
          id="mobile-nav"
          aria-label="Мобильная навигация"
          hidden={!menu}
        >
          {links}
          <button
            className={cx("header-action")}
            onClick={() => {
              setSearch(true);
              setMenu(false);
            }}
          >
            Поиск по каталогу
          </button>
        </nav>
        <form
          hidden={!search}
          inert={!search}
          className={cx("searchbar", "shell")}
          onSubmit={(e) => {
            e.preventDefault();
            navigate("/catalog?q=" + encodeURIComponent(query));
          }}
        >
          <label htmlFor="site-search">Найти вещь</label>
          <input
            className={cx("input")}
            id="site-search"
            type="search"
            placeholder="Название вещи"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit">Найти</button>
          <button
            type="button"
            onClick={() => {
              setQuery("");
              navigate("/catalog");
            }}
          >
            Очистить
          </button>
          <button type="button" onClick={() => setSearch(false)}>
            Закрыть
          </button>
        </form>
      </div>
      <main id="main">{children}</main>
      <footer className={cx("footer")}>
        <div className={cx("shell")}>
          <div className={cx("footer-upper")}>
            <div>
              <div className={cx("footer-brand")}>
                <Logo variant="footer" />
              </div>
              <p className={cx("footer-brand-sub")}>
                Одежда, свободная от лишнего.
              </p>
            </div>
            <div className={cx("footer-col")}>
              <h3>Магазин</h3>
              <Link to="/catalog">Коллекция</Link>
              <Link to="/#manifesto">О бренде</Link>
              <Link to="/delivery">Доставка и оплата</Link>
              <Link to="/contacts">Контакты</Link>
              <button onClick={() => cart.setOpen(true)}>Моя корзина</button>
            </div>
            <div className={cx("footer-col")}>
              <h3>Информация</h3>
              <Link to="/documents/offer">Условия покупки</Link>
              <Link to="/documents/privacy">Конфиденциальность</Link>
              <Link to="/documents/returns">Обмен и возврат</Link>
              {store?.email && (
                <a href={"mailto:" + store.email}>{store.email}</a>
              )}
            </div>
          </div>
          <div className={cx("footer-bottom")}>
            <span>
              © {new Date().getFullYear()} {store?.brand ?? "ATELIER NOIR"}
            </span>
            <span>Форма. Свобода. Характер.</span>
          </div>
        </div>
      </footer>
      {cart.open && <CartDrawer />}
      <div
        className={cx("toast", !!cart.toast && "show")}
        role="status"
        aria-live="polite"
      >
        {cart.toast}
      </div>
    </div>
  );
}
