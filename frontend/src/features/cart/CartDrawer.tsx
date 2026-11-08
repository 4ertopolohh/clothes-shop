import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useCart } from "./CartContext";
import type { Quote } from "../../types";
import { post } from "../../api/client";
import { cx, Drawer, ErrorState, fmt } from "../../components/ui";
import { Skeleton, SmartImage, Spinner } from "../../components/Skeleton";
export function CartDrawer() {
  const cart = useCart();
  const navigate = useNavigate();
  const [input, setInput] = useState(cart.promo),
    [quote, setQuote] = useState<Quote>(),
    [error, setError] = useState<Error>(),
    [loading, setLoading] = useState(false),
    [retry, setRetry] = useState(0);
  const payload = JSON.stringify({
    items: cart.lines.map((x) => ({
      variant_id: x.variant_id,
      quantity: x.quantity,
    })),
    promo: cart.promo,
  });
  useEffect(() => {
    if (!cart.lines.length) return;
    const abort = new AbortController();
    setLoading(true);
    setError(undefined);
    post<Quote>("/quote/", JSON.parse(payload), abort.signal)
      .then((data) => {
        setQuote(data);
        setLoading(false);
      })
      .catch((e: Error) => {
        if (e.name !== "AbortError") {
          setError(e);
          setLoading(false);
        }
      });
    return () => abort.abort();
  }, [payload, retry, cart.lines.length]);
  return (
    <Drawer title="Ваша корзина" onClose={() => cart.setOpen(false)}>
      {cart.lines.length ? (
        <>
          <div>
            {cart.lines.map((line) => {
              const v = line.product.variants.find(
                (x) => x.id === line.variant_id,
              );
              return (
                <article className={cx("cart-item")} key={line.variant_id}>
                  <div className={cx("cart-image")}>
                    <SmartImage
                      src={line.product.images[0]?.url ?? ""}
                      alt={line.product.name}
                    />
                  </div>
                  <div>
                    <Link
                      className={cx("cart-item-name")}
                      to={"/product/" + line.product.slug}
                      onClick={() => cart.setOpen(false)}
                    >
                      {line.product.name}
                    </Link>
                    <p className={cx("subdued")}>
                      {v?.color} · {v?.size}
                    </p>
                    <div className={cx("cart-line-bottom")}>
                      <div className={cx("stepper")}>
                        <button
                          aria-label={
                            "Уменьшить количество: " + line.product.name
                          }
                          disabled={line.quantity <= 1}
                          onClick={() =>
                            cart.quantity(line.variant_id, line.quantity - 1)
                          }
                        >
                          −
                        </button>
                        <output>{line.quantity}</output>
                        <button
                          aria-label={
                            "Увеличить количество: " + line.product.name
                          }
                          disabled={
                            line.quantity >= Math.min(30, v?.available ?? 30)
                          }
                          onClick={() =>
                            cart.quantity(line.variant_id, line.quantity + 1)
                          }
                        >
                          +
                        </button>
                      </div>
                      <span className={cx("price-strong")}>
                        {fmt(Number(v?.price ?? 0) * line.quantity)}
                      </span>
                    </div>
                    <button
                      className={cx("remove-btn")}
                      onClick={() => cart.remove(line.variant_id)}
                    >
                      Удалить
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
          <label className={cx("form-label")} htmlFor="promo">
            Промокод
          </label>
          <div className={cx("promo-row")}>
            <input
              id="promo"
              className={cx("input")}
              maxLength={40}
              placeholder="Введите промокод"
              value={input}
              onChange={(e) => setInput(e.target.value.toUpperCase())}
            />
            <button
              className={cx("outline-btn")}
              disabled={loading}
              onClick={() => {
                cart.setPromo(input.trim());
                setRetry((x) => x + 1);
              }}
            >
              Применить
            </button>
          </div>
          {cart.promo && (
            <p className={cx("promo-message")}>
              <button
                className={cx("link-btn")}
                onClick={() => {
                  cart.setPromo("");
                  setInput("");
                }}
              >
                Убрать промокод {cart.promo}
              </button>
            </p>
          )}
          {error && (
            <ErrorState error={error} retry={() => setRetry((x) => x + 1)} />
          )}
          <div className={cx("cart-summary")} aria-busy={loading}>
            <div className={cx("cart-row")}>
              <span>Товары</span>
              {loading ? (
                <Skeleton />
              ) : (
                <span>{fmt(quote?.subtotal ?? 0)}</span>
              )}
            </div>
            {Number(quote?.discount) > 0 && (
              <div className={cx("cart-row")}>
                <span>Скидка</span>
                <span>−{fmt(quote!.discount)}</span>
              </div>
            )}
            <div className={cx("cart-row")}>
              <span>Доставка</span>
              <span>Рассчитаем при оформлении</span>
            </div>
            <div className={cx("cart-row", "total")}>
              <span>Промежуточный итог</span>
              {loading ? <Skeleton /> : <span>{fmt(quote?.total ?? 0)}</span>}
            </div>
            <button
              className={cx("primary-btn", "full")}
              disabled={loading || !!error || !quote}
              onClick={() => {
                cart.setOpen(false);
                navigate("/checkout");
              }}
            >
              {loading && <Spinner />}Перейти к оформлению
            </button>
            <p className={cx("checkout-note")}>
              Вещи сохраняются в этом браузере. Остатки проверим перед
              оформлением заказа.
            </p>
          </div>
        </>
      ) : (
        <div className={cx("empty-cart")}>
          <h3>Пока пусто</h3>
          <p>Вещи, которые вы выберете, появятся здесь.</p>
          <Link
            className={cx("primary-btn")}
            to="/#catalog"
            onClick={() => cart.setOpen(false)}
          >
            К коллекции
          </Link>
        </div>
      )}
    </Drawer>
  );
}
