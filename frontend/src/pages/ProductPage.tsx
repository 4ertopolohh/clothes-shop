import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useResource } from "../hooks/useResource";
import type { Product } from "../types";
import { useCart } from "../features/cart/CartContext";
import { cx, fmt, Drawer, ErrorState } from "../components/ui";
import { PageSkeleton, SmartImage, Skeleton } from "../components/Skeleton";
export function ProductPage({ modal = false }: { modal?: boolean }) {
  const { slug } = useParams();
  const navigate = useNavigate();
  const resource = useResource<Product>("/products/" + slug + "/");
  const cart = useCart();
  const [color, setColor] = useState(""),
    [size, setSize] = useState(""),
    [quantity, setQuantity] = useState(1),
    [photo, setPhoto] = useState(0),
    [error, setError] = useState("");
  useEffect(() => {
    const previousTitle = document.title;
    if (resource.data) {
      setColor(resource.data.variants[0]?.color ?? "");
      setSize("");
      setQuantity(1);
      setPhoto(0);
      document.title = resource.data.name + " · ATELIER NOIR";
    }
    return () => {
      document.title = previousTitle;
    };
  }, [resource.data]);
  const product = resource.data;
  const colors = product
    ? [...new Map(product.variants.map((v) => [v.color, v])).values()]
    : [];
  const sizes = product
    ? [...new Set(product.variants.map((v) => v.size))]
    : [];
  const selected = product?.variants.find(
    (v) => v.color === color && v.size === size,
  );
  const content = resource.loading ? (
    <div className={cx("product-detail")}>
      <div className={cx("detail-visual")}>
        <Skeleton kind="fill" />
      </div>
      <div className={cx("detail-info")}>
        <PageSkeleton />
      </div>
    </div>
  ) : resource.error ? (
    <ErrorState error={resource.error} retry={resource.retry} />
  ) : (
    product && (
      <>
        <div className={cx("product-detail")}>
          <div className={cx("detail-visual")}>
            <SmartImage
              key={product.images[photo]?.url}
              src={product.images[photo]?.url ?? ""}
              alt={product.images[photo]?.alt ?? product.name}
              eager
            />
            {product.images.length > 1 && (
              <div className={cx("thumbnails")}>
                {product.images.map((image, i) => (
                  <button
                    key={image.url}
                    aria-label={"Фотография " + (i + 1)}
                    aria-pressed={photo === i}
                    onClick={() => setPhoto(i)}
                  >
                    <img src={image.url} alt="" />
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className={cx("detail-info")}>
            {!modal && <h1 className={cx("product-title")}>{product.name}</h1>}
            <p className={cx("detail-price")}>
              {fmt(selected?.price ?? product.price)}
            </p>
            <p className={cx("detail-desc")}>{product.description}</p>
            <fieldset className={cx("choice-fieldset")}>
              <legend className={cx("detail-choice-label")}>
                Цвет: {color}
              </legend>
              <div className={cx("color-options")}>
                {colors.map((v) => (
                  <button
                    type="button"
                    key={v.color}
                    className={cx("swatch", color === v.color && "active")}
                    style={{ background: v.color_hex }}
                    aria-label={v.color}
                    aria-pressed={color === v.color}
                    onClick={() => {
                      setColor(v.color);
                      setSize("");
                      setError("");
                      setQuantity(1);
                    }}
                  />
                ))}
              </div>
            </fieldset>
            <fieldset className={cx("choice-fieldset")}>
              <legend className={cx("detail-choice-label")}>Размер</legend>
              <div className={cx("size-options")}>
                {sizes.map((option) => {
                  const variant = product.variants.find(
                    (v) => v.color === color && v.size === option,
                  );
                  return (
                    <button
                      type="button"
                      className={cx("size-btn", size === option && "selected")}
                      key={option}
                      disabled={!variant?.available}
                      aria-pressed={size === option}
                      onClick={() => {
                        setSize(option);
                        setQuantity(1);
                        setError("");
                      }}
                    >
                      {option}
                    </button>
                  );
                })}
              </div>
            </fieldset>
            <div className={cx("detail-quantity")}>
              <span>
                {selected
                  ? `Доступно: ${selected.available} шт.`
                  : "Выберите размер"}
              </span>
              <div className={cx("stepper")}>
                <button
                  aria-label="Уменьшить количество"
                  disabled={quantity <= 1}
                  onClick={() => setQuantity((x) => x - 1)}
                >
                  −
                </button>
                <output aria-label="Количество">{quantity}</output>
                <button
                  aria-label="Увеличить количество"
                  disabled={
                    !selected || quantity >= Math.min(30, selected.available)
                  }
                  onClick={() => setQuantity((x) => x + 1)}
                >
                  +
                </button>
              </div>
            </div>
            {error && (
              <p className={cx("detail-error")} role="alert">
                {error}
              </p>
            )}
            <button
              className={cx("primary-btn", "full")}
              disabled={!product.variants.some((v) => v.available > 0)}
              onClick={() => {
                if (!selected) {
                  setError("Выберите размер вещи.");
                  return;
                }
                cart.add(product, selected, quantity);
              }}
            >
              Добавить в корзину
            </button>
            <button
              className={cx("link-btn", "cart-shortcut")}
              onClick={() => {
                if (modal) navigate(-1);
                cart.setOpen(true);
              }}
            >
              Открыть корзину
            </button>
            <dl className={cx("characteristics")}>
              {Object.entries(product.characteristics).map(([key, value]) => (
                <div key={key}>
                  <dt>{key}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
            <p className={cx("field-hint")}>
              Точный остаток и итог проверяются при оформлении.
            </p>
          </div>
        </div>
        {!modal && (
          <Link className={cx("back-link")} to="/#catalog">
            Вернуться к коллекции
          </Link>
        )}
      </>
    )
  );
  return modal ? (
    <Drawer
      title={product?.name ?? "Выбор вещи"}
      wide
      onClose={() => navigate(-1)}
    >
      {content}
    </Drawer>
  ) : (
    <section className={cx("product-page", "shell")}>{content}</section>
  );
}
