import { Link } from "react-router-dom";
import type { Product } from "../../types";
import { cx, fmt, Reveal } from "../../components/ui";
import { SmartImage } from "../../components/Skeleton";
export function ProductCard({
  product,
  index = 0,
}: {
  product: Product;
  index?: number;
}) {
  const colors = [
    ...new Map(product.variants.map((v) => [v.color, v])).values(),
  ];
  return (
    <Reveal variant="scale-in" delay={(index % 3) * 85}>
      <article className={cx("product-card")}>
        <Link
          className={cx("product-photo")}
          to={"/product/" + product.slug}
          aria-label={"Подробнее: " + product.name}
        >
          <SmartImage
            key={product.images[0]?.url}
            src={product.images[0]?.url ?? ""}
            alt={product.images[0]?.alt ?? product.name}
          />
          {product.badge && (
            <span className={cx("product-badge")}>{product.badge}</span>
          )}
          <span className={cx("quick-view")}>Посмотреть вещь</span>
        </Link>
        <div className={cx("product-meta")}>
          <Link className={cx("product-name")} to={"/product/" + product.slug}>
            {product.name}
          </Link>
          <div className={cx("product-category")}>{product.category}</div>
          <div className={cx("product-bottom")}>
            <span className={cx("product-price")}>{fmt(product.price)}</span>
            <span
              className={cx("mini-swatches")}
              aria-label={"Цвета: " + colors.map((x) => x.color).join(", ")}
            >
              {colors.map((v) => (
                <i key={v.color} style={{ background: v.color_hex }} />
              ))}
            </span>
          </div>
        </div>
      </article>
    </Reveal>
  );
}
