import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useCart } from "../features/cart/CartContext";
import { request, post } from "../api/client";
import type { City, Pickup, Quote, Order, Product, CartLine } from "../types";
import { cx, ErrorState, Select, fmt } from "../components/ui";
import { Skeleton, Spinner } from "../components/Skeleton";
export function CheckoutPage() {
  const cart = useCart(),
    navigate = useNavigate();
  const [params] = useSearchParams();
  const buyNow = params.get("mode") === "buy-now";
  const slug = params.get("product") ?? "";
  const variantText = params.get("variant") ?? "";
  const quantityText = params.get("quantity") ?? "";
  const validParams = /^[a-zA-Z0-9_-]+$/.test(slug) && /^[1-9]\d*$/.test(variantText) && /^[1-9]\d*$/.test(quantityText) && Number.isSafeInteger(Number(variantText)) && Number(quantityText) <= 30;
  const [quickProduct, setQuickProduct] = useState<Product>();
  const [quickError, setQuickError] = useState<Error>();
  const [quickLoading, setQuickLoading] = useState(buyNow && validParams);
  useEffect(() => {
    if (!buyNow || !validParams) return;
    const controller = new AbortController();
    setQuickLoading(true); setQuickError(undefined); setQuickProduct(undefined);
    request<Product>("/products/" + encodeURIComponent(slug) + "/", { signal: controller.signal }).then(setQuickProduct).catch((e: Error) => { if (e.name !== "AbortError") setQuickError(e); }).finally(() => { if (!controller.signal.aborted) setQuickLoading(false); });
    return () => controller.abort();
  }, [buyNow, slug, variantText, quantityText, validParams]);
  const variant = quickProduct?.variants.find(v => v.id === Number(variantText));
  const quickValid = !!variant && variant.available >= Number(quantityText);
  const lines: CartLine[] = buyNow ? (quickProduct && quickValid ? [{ product: quickProduct, variant_id: Number(variantText), quantity: Number(quantityText) }] : []) : cart.lines;
  const promo = buyNow ? "" : cart.promo;
  const key = useRef(crypto.randomUUID());
  const submitting = useRef(false);
  const [cityQuery, setCityQuery] = useState(""),
    [cities, setCities] = useState<City[]>([]),
    [city, setCity] = useState<City>(),
    [cityLoading, setCityLoading] = useState(false),
    [cityError, setCityError] = useState<Error>();
  const [points, setPoints] = useState<Pickup[]>([]),
    [point, setPoint] = useState(""),
    [pointLoading, setPointLoading] = useState(false),
    [pointError, setPointError] = useState<Error>();
  const [method, setMethod] = useState("pickup"),
    [address, setAddress] = useState(""),
    [quote, setQuote] = useState<Quote>(),
    [quoteLoading, setQuoteLoading] = useState(false),
    [quoteError, setQuoteError] = useState<Error>(),
    [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState<Error>();
  useEffect(() => {
    document.title = "Оформление заказа · ATELIER NOIR";
  }, []);
  useEffect(() => {
    if (city || cityQuery.trim().length < 2) {
      setCities([]);
      return;
    }
    const abort = new AbortController();
    const timer = setTimeout(() => {
      setCityLoading(true);
      setCityError(undefined);
      request<City[]>("/shipping/cities/?q=" + encodeURIComponent(cityQuery), {
        signal: abort.signal,
      })
        .then((xs) => {
          setCities(xs);
          setCityLoading(false);
        })
        .catch((e: Error) => {
          if (e.name !== "AbortError") {
            setCityError(e);
            setCityLoading(false);
          }
        });
    }, 300);
    return () => {
      clearTimeout(timer);
      abort.abort();
    };
  }, [cityQuery, city, revision]);
  useEffect(() => {
    setPoint("");
    setPoints([]);
    if (!city || method !== "pickup") return;
    const abort = new AbortController();
    setPointLoading(true);
    setPointError(undefined);
    request<Pickup[]>("/shipping/points/?city_code=" + city.code, {
      signal: abort.signal,
    })
      .then((xs) => {
        setPoints(xs);
        setPointLoading(false);
      })
      .catch((e: Error) => {
        if (e.name !== "AbortError") {
          setPointError(e);
          setPointLoading(false);
        }
      });
    return () => abort.abort();
  }, [city, method, revision]);
  const payload = JSON.stringify({
    items: lines.map((x) => ({
      variant_id: x.variant_id,
      quantity: x.quantity,
    })),
    promo,
    city_code: city?.code,
    delivery_method: method,
  });
  useEffect(() => {
    if (!lines.length) return;
    const abort = new AbortController();
    setQuoteLoading(true);
    setQuoteError(undefined);
    post<Quote>("/quote/", JSON.parse(payload), abort.signal)
      .then((data) => {
        setQuote(data);
        setQuoteLoading(false);
      })
      .catch((e: Error) => {
        if (e.name !== "AbortError") {
          setQuoteError(e);
          setQuoteLoading(false);
        }
      });
    return () => abort.abort();
  }, [payload, lines.length, revision]);
  if (buyNow && (quickLoading || !validParams || quickError || !quickValid)) return <section className={cx("content-page", "shell")}><h1>Быстрая покупка</h1>{quickLoading ? <Skeleton kind="block" /> : <><p role="alert">Не удалось выбрать товар: проверьте ссылку и наличие варианта.</p><Link className={cx("primary-btn")} to={validParams ? "/product/" + encodeURIComponent(slug) : "/catalog"}>Вернуться к выбору</Link></>}</section>;
  if (!lines.length)
    return (
      <section className={cx("content-page", "shell")}>
        <h1>Корзина пока пуста</h1>
        <p>Выберите вещи, чтобы перейти к оформлению.</p>
        <Link className={cx("primary-btn")} to="/catalog">
          К коллекции
        </Link>
      </section>
    );
  const selectedPoint = points.find((x) => x.code === point);
  return (
    <section className={cx("content-page", "shell")}>
      <h1>Оформление заказа</h1>
      <div className={cx("checkout-layout")}>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            if (submitting.current) return;
            if (!city || (method === "pickup" && !point)) {
              setError(new Error("Выберите город и пункт выдачи."));
              return;
            }
            const form = new FormData(e.currentTarget);
            submitting.current = true;
            setBusy(true);
            setError(undefined);
            try {
              const order = await post<Order>("/orders/", {
                ...JSON.parse(payload),
                request_key: key.current,
                name: form.get("name"),
                email: form.get("email"),
                phone: form.get("phone"),
                city: city.city,
                pickup_code: point,
                address,
                comment: form.get("comment"),
                consent: form.get("consent") === "on",
              });
              if (!buyNow) cart.clear();
              navigate("/order/" + order.token, { replace: true });
            } catch (e) {
              setError(e as Error);
            } finally {
              submitting.current = false;
              setBusy(false);
            }
          }}
        >
          <div className={cx("form-grid")}>
            <div className={cx("field")}>
              <label className={cx("form-label")} htmlFor="name">
                Имя и фамилия
              </label>
              <input
                id="name"
                name="name"
                className={cx("input")}
                autoComplete="name"
                required
                minLength={2}
                maxLength={150}
              />
            </div>
            <div className={cx("field")}>
              <label className={cx("form-label")} htmlFor="phone">
                Телефон
              </label>
              <input
                id="phone"
                name="phone"
                type="tel"
                className={cx("input")}
                autoComplete="tel"
                required
                placeholder="+7 999 123-45-67"
                maxLength={30}
              />
            </div>
          </div>
          <div className={cx("field")}>
            <label className={cx("form-label")} htmlFor="email">
              Электронная почта
            </label>
            <input
              id="email"
              name="email"
              type="email"
              className={cx("input")}
              autoComplete="email"
              required
              maxLength={254}
            />
            <p className={cx("field-hint")}>
              На этот адрес отправим подтверждение заказа и оплаты.
            </p>
          </div>
          <fieldset className={cx("choice-fieldset", "field")}>
            <legend className={cx("form-label")}>Способ получения</legend>
            <div className={cx("delivery-choices")}>
              {[
                { value: "pickup", label: "В пункте выдачи СДЭК" },
                { value: "courier", label: "Курьером СДЭК" },
              ].map((x) => (
                <label
                  className={cx(
                    "delivery-choice",
                    method === x.value && "selected",
                  )}
                  key={x.value}
                >
                  <input
                    type="radio"
                    name="delivery"
                    checked={method === x.value}
                    onChange={() => setMethod(x.value)}
                  />
                  {x.label}
                </label>
              ))}
            </div>
          </fieldset>
          <div className={cx("field", "city-field")}>
            <label className={cx("form-label")} htmlFor="city">
              Город доставки
            </label>
            <input
              id="city"
              className={cx("input")}
              autoComplete="off"
              required
              placeholder="Начните вводить название"
              value={cityQuery}
              onChange={(e) => {
                setCity(undefined);
                setCityQuery(e.target.value);
                setCityLoading(false);
              }}
              aria-autocomplete="list"
              aria-controls="city-results"
              aria-expanded={cities.length > 0}
            />
            {cityLoading && (
              <div className={cx("city-loading")}>
                <Skeleton />
              </div>
            )}
            {cities.length > 0 && (
              <ul
                id="city-results"
                className={cx("city-results")}
                aria-label="Найденные города"
              >
                {cities.map((c) => (
                  <li key={c.code}>
                    <button
                      type="button"
                      onClick={() => {
                        setCity(c);
                        setCityQuery(c.city);
                        setCities([]);
                      }}
                    >
                      {c.city}
                      {c.region ? " · " + c.region : ""}
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {cityError && (
              <ErrorState
                error={cityError}
                retry={() => setRevision((x) => x + 1)}
              />
            )}
            <p className={cx("field-hint")}>
              {city
                ? "Город выбран."
                : "Введите не менее двух букв и выберите город из списка."}
            </p>
          </div>
          {method === "pickup" ? (
            <div className={cx("field")}>
              <label className={cx("form-label")}>Пункт выдачи СДЭК</label>
              {pointLoading ? (
                <Skeleton kind="block" />
              ) : (
                <Select
                  label="Выберите пункт выдачи"
                  value={point}
                  disabled={!city || !points.length}
                  options={[
                    {
                      value: "",
                      label: city
                        ? "Выберите пункт выдачи"
                        : "Сначала выберите город",
                    },
                    ...points.map((p) => ({ value: p.code, label: p.address })),
                  ]}
                  onChange={setPoint}
                />
              )}
              <div aria-live="polite">
                {selectedPoint && (
                  <p className={cx("pickup-info")}>
                    {selectedPoint.name}
                    <br />
                    {selectedPoint.address}
                    <br />
                    {selectedPoint.hours}
                  </p>
                )}
                {city && !pointLoading && !pointError && !points.length && (
                  <p>
                    Пункты выдачи не найдены. Выберите курьерскую доставку или
                    другой город.
                  </p>
                )}
              </div>
              {pointError && (
                <ErrorState
                  error={pointError}
                  retry={() => setRevision((x) => x + 1)}
                />
              )}
            </div>
          ) : (
            <div className={cx("field")}>
              <label className={cx("form-label")} htmlFor="address">
                Улица, дом, квартира
              </label>
              <input
                id="address"
                className={cx("input")}
                autoComplete="street-address"
                required
                minLength={8}
                maxLength={400}
                value={address}
                onChange={(e) => setAddress(e.target.value)}
              />
            </div>
          )}
          <div className={cx("field")}>
            <label className={cx("form-label")} htmlFor="comment">
              Комментарий к заказу
            </label>
            <textarea
              id="comment"
              name="comment"
              className={cx("input")}
              rows={3}
              maxLength={2000}
            />
          </div>
          <label className={cx("legal-check")}>
            <input type="checkbox" name="consent" required />
            <span>
              Принимаю{" "}
              <Link
                target="_blank"
                rel="noopener noreferrer"
                to="/documents/offer"
              >
                условия покупки
              </Link>{" "}
              и соглашаюсь с{" "}
              <Link
                target="_blank"
                rel="noopener noreferrer"
                to="/documents/privacy"
              >
                обработкой персональных данных
              </Link>{" "}
              для оформления заказа.
            </span>
          </label>
          {error && <ErrorState error={error} />}
          <button
            className={cx("primary-btn", "full")}
            type="submit"
            disabled={
              busy ||
              quoteLoading ||
              !!quoteError ||
              !city ||
              (method === "pickup" && !point)
            }
          >
            {busy && <Spinner />}
            {busy ? "Оформляем заказ…" : "Оформить заказ"}
          </button>
          <p className={cx("checkout-note")}>
            Проверим доступность вещей и сохраним заказ. К оплате можно будет
            перейти на следующем шаге.
          </p>
        </form>
        <aside className={cx("order-summary")} aria-label="Ваш заказ">
          <h2>Ваш выбор</h2>
          {lines.map((x) => (
            <div className={cx("summary-item")} key={x.variant_id}>
              <span>
                {x.product.name}
                <small>
                  {x.product.variants.find((v) => v.id === x.variant_id)?.size}{" "}
                  ·{" "}
                  {x.product.variants.find((v) => v.id === x.variant_id)?.color}{" "}
                  · {x.quantity} шт.
                </small>
              </span>
            </div>
          ))}
          {quoteError ? (
            <ErrorState
              error={quoteError}
              retry={() => setRevision((x) => x + 1)}
            />
          ) : quoteLoading ? (
            <>
              <Skeleton />
              <Skeleton />
              <Skeleton />
            </>
          ) : (
            quote && (
              <>
                <div className={cx("cart-row")}>
                  <span>Товары</span>
                  <span>{fmt(quote.subtotal)}</span>
                </div>
                {Number(quote.discount) > 0 && (
                  <div className={cx("cart-row")}>
                    <span>Скидка {promo}</span>
                    <span>−{fmt(quote.discount)}</span>
                  </div>
                )}
                <div className={cx("cart-row")}>
                  <span>Доставка</span>
                  <span>
                    {city ? fmt(quote.shipping_cost) : "Выберите город"}
                  </span>
                </div>
                <div className={cx("cart-row", "total")}>
                  <span>Итого</span>
                  <span>{fmt(quote.total)}</span>
                </div>
                {quote.delivery_days && (
                  <p className={cx("field-hint")}>{quote.delivery_days}</p>
                )}
              </>
            )
          )}
        </aside>
      </div>
    </section>
  );
}
