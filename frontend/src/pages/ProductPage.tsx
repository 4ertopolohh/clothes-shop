import { useEffect, useState, useRef } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useResource } from "../hooks/useResource";
import type { Product } from "../types";
import { useCart } from "../features/cart/CartContext";
import { cx, fmt, Drawer, ErrorState } from "../components/ui";
import { PageSkeleton, SmartImage, Skeleton } from "../components/Skeleton";
export function ProductPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const resource = useResource<Product>("/products/" + slug + "/");
  const cart = useCart();
  const [lightbox, setLightbox] = useState(false);
  const touch = useRef<number | null>(null);
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
  const movePhoto = (direction: number) => setPhoto((current) => product?.images.length ? (current + direction + product.images.length) % product.images.length : 0);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "ArrowLeft") movePhoto(-1);
      if (event.key === "ArrowRight") movePhoto(1);
    };
    if (lightbox) window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [lightbox, product]);
  const galleryImage = product?.images[photo];
  const controls = product && product.images.length > 1 && <div className={cx("gallery-controls")}><button type="button" onClick={() => movePhoto(-1)} aria-label="Предыдущее фото">←</button><span aria-live="polite">{photo + 1} / {product.images.length}</span><button type="button" onClick={() => movePhoto(1)} aria-label="Следующее фото">→</button></div>;
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
            <div className={cx("gallery-main")} onTouchStart={(e) => { touch.current = e.touches[0].clientX; }} onTouchEnd={(e) => { if (touch.current !== null && Math.abs(e.changedTouches[0].clientX - touch.current) > 50) movePhoto(e.changedTouches[0].clientX < touch.current ? 1 : -1); touch.current = null; }} onKeyDown={(e) => { if (e.key === "ArrowLeft") movePhoto(-1); if (e.key === "ArrowRight") movePhoto(1); }}>
              <button className={cx("gallery-image")} type="button" disabled={!galleryImage} onClick={() => setLightbox(true)} aria-label="Открыть фотографию на весь экран"><SmartImage key={galleryImage?.url} src={galleryImage?.url ?? ""} alt={galleryImage?.alt ?? product.name} eager /></button>
              {controls}
            </div>
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
            <p>{product.category}</p><h1 className={cx("product-title")}>{product.name}</h1>
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
            <button className={cx("outline-btn", "full", "buy-now")} disabled={!product.variants.some((v) => v.available > 0)} onClick={() => {
              if (!selected || selected.available < quantity) { setError("Выберите доступный размер вещи."); return; }
              navigate(`/checkout?mode=buy-now&product=${encodeURIComponent(product.slug)}&variant=${selected.id}&quantity=${quantity}`);
            }}>Купить сейчас</button>
            <button
              className={cx("link-btn", "cart-shortcut")}
              onClick={() => {
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
        {lightbox && galleryImage && <Drawer title={`Фотография ${photo + 1} из ${product.images.length}`} fullscreen onClose={() => setLightbox(false)}><div className={cx("lightbox-image")} onTouchStart={(e) => { touch.current = e.touches[0].clientX; }} onTouchEnd={(e) => { if (touch.current !== null && Math.abs(e.changedTouches[0].clientX - touch.current) > 50) movePhoto(e.changedTouches[0].clientX < touch.current ? 1 : -1); touch.current = null; }}><SmartImage key={galleryImage.url} src={galleryImage.url} alt={galleryImage.alt || product.name} eager />{controls}</div></Drawer>}
      </>
    )
  );
  return <section className={cx("product-page", "shell")}><Link className={cx("back-link")} to="/catalog">← Вернуться к коллекции</Link>{content}</section>;
}
