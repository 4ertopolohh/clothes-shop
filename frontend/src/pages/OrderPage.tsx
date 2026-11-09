import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useResource } from "../hooks/useResource";
import { post } from "../api/client";
import type { Order } from "../types";
import { cx, fmt, ErrorState } from "../components/ui";
import { PageSkeleton, Spinner } from "../components/Skeleton";
export function OrderPage({
  localPayment = false,
}: {
  localPayment?: boolean;
}) {
  const { token } = useParams();
  const navigate = useNavigate();
  const resource = useResource<Order>(
    "/orders/" + token + "/" + (localPayment ? "local-payment/" : ""),
  );
  const [busy, setBusy] = useState(false),
    [error, setError] = useState<Error>();
  useEffect(() => {
    document.title = "Ваш заказ · ATELIER NOIR";
  }, []);
  const order = resource.data;
  return (
    <section className={cx("content-page", "receipt-page", "shell")}>
      {resource.loading ? (
        <PageSkeleton />
      ) : resource.error ? (
        <ErrorState error={resource.error} retry={resource.retry} />
      ) : (
        order && (
          <>
            <h1>
              {localPayment
                ? "Проверка оплаты"
                : order.status === "paid"
                  ? "Спасибо за ваш выбор."
                  : order.status === "canceled"
                    ? "Заказ отменён."
                    : "Ваш заказ сохранён."}
            </h1>
            <p className={cx("order-number")}>
              {order.number} · {order.status_label}
            </p>
            {localPayment && (
              <p>
                Здесь можно проверить оплату заказа без списания денежных
                средств.
              </p>
            )}
            <div className={cx("receipt-items")}>
              {order.items.map((item, i) => (
                <div className={cx("summary-item")} key={i}>
                  <span>
                    {item.name}
                    <small>
                      {item.color} · {item.size} · {item.quantity} шт.
                    </small>
                  </span>
                  <strong>{fmt(item.total)}</strong>
                </div>
              ))}
            </div>
            <div className={cx("cart-row")}>
              <span>Товары</span>
              <span>{fmt(order.subtotal)}</span>
            </div>
            {Number(order.discount) > 0 && (
              <div className={cx("cart-row")}>
                <span>Скидка</span>
                <span>−{fmt(order.discount)}</span>
              </div>
            )}
            <div className={cx("cart-row")}>
              <span>Доставка</span>
              <span>{fmt(order.shipping_cost)}</span>
            </div>
            <div className={cx("cart-row", "total")}>
              <span>Итого</span>
              <span>{fmt(order.total)}</span>
            </div>
            <p>
              {order.delivery_method}
              <br />
              {order.delivery_address}
              <br />
              {order.delivery_days}
            </p>
            {order.tracking && <p>Отправление СДЭК: {order.tracking}</p>}
            {order.status === "pending" && (
              <p className={cx("checkout-note")}>
                Резерв до {new Date(order.expires_at).toLocaleString("ru-RU")}.
                Сохраните ссылку на эту страницу: здесь доступны детали и статус
                заказа.
              </p>
            )}
            {error && <ErrorState error={error} />}
            <div className={cx("receipt-actions")}>
              {order.status === "pending" && (
                <button
                  className={cx("primary-btn")}
                  disabled={busy}
                  onClick={async () => {
                    setBusy(true);
                    setError(undefined);
                    try {
                      if (localPayment) {
                        await post("/orders/" + token + "/local-payment/");
                        navigate("/order/" + token, { replace: true });
                      } else {
                        const result = await post<{ url: string }>(
                          "/orders/" + token + "/payment/",
                        );
                        if (result.url.startsWith("/")) navigate(result.url);
                        else window.location.assign(result.url);
                      }
                    } catch (e) {
                      setError(e as Error);
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  {busy && <Spinner />}
                  {localPayment
                    ? "Подтвердить без списания"
                    : "Перейти к оплате"}
                </button>
              )}
              {!localPayment && (
                <button className={cx("outline-btn")} onClick={resource.retry}>
                  Проверить статус
                </button>
              )}
              <Link className={cx("link-btn")} to="/catalog">
                Вернуться к коллекции
              </Link>
            </div>
          </>
        )
      )}
    </section>
  );
}
