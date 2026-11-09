import { Link } from "react-router-dom";
import { useStore } from "../app/StoreContext";
import { cx, Reveal, ErrorState } from "../components/ui";
import { Skeleton, SmartImage } from "../components/Skeleton";
import { ProductCard } from "../features/catalog/ProductCard";
import { useResource } from "../hooks/useResource";
import type { CatalogResponse } from "../types";
import { CatalogSkeleton } from "../components/Skeleton";
export function HomePage() {
  const { data: store, error, retry } = useStore();
  const news = useResource<CatalogResponse>("/catalog/?new=1&page=1");
  return (
    <>
      {error && <ErrorState error={error} retry={retry} />}
      <section className={cx("hero", "shell")} aria-labelledby="hero-title">
        <div className={cx("hero-image")}>
          {store ? (
            <SmartImage
              key={store.hero_image}
              src={store.hero_image}
              alt="Образ ATELIER NOIR в городском пространстве"
              eager
            />
          ) : (
            <Skeleton kind="fill" />
          )}
        </div>
        <div className={cx("hero-copy")}>
          <div />
          <div>
            {store ? (
              <h1 id="hero-title">{store.hero_title}</h1>
            ) : (
              <Skeleton kind="title" />
            )}
            {store ? (
              <p>{store.hero_text}</p>
            ) : (
              <>
                <Skeleton />
                <Skeleton />
                <Skeleton />
              </>
            )}
            <Link className={cx("outline-light")} to="/catalog">
              Исследовать коллекцию
            </Link>
          </div>
          <div className={cx("hero-bottom")}>
            <div className={cx("hero-mark")}>AN.</div>
            <div className={cx("hero-note")}>
              Тихий характер.
              <br />
              Выразительная форма.
            </div>
          </div>
        </div>
      </section>
      <div className={cx("trustline", "shell")}>
        <span>Подберите размер и цвет онлайн</span>
        <span>Добавляйте несколько вещей в корзину</span>
        <span>Выбирайте удобный способ доставки</span>
      </div>
      <section className={cx("catalog-section", "shell")} aria-labelledby="new-title">
        <Reveal className={cx("catalog-heading")}><h2 id="new-title" className={cx("section-title")}>Новинки</h2><Link className={cx("link-btn")} to="/catalog?new=1">Все новинки</Link></Reveal>
        {news.loading ? <CatalogSkeleton /> : news.error ? <ErrorState error={news.error} retry={news.retry} /> : news.data?.results.length ? <div className={cx("products")}>{news.data.results.slice(0, 6).map(product => <ProductCard key={product.id} product={product} />)}</div> : <p>Новые вещи скоро появятся здесь.</p>}
        <Link className={cx("show-more")} to="/catalog">Смотреть все товары</Link>
      </section>
      <section
        className={cx("editorial", "shell")}
        id="manifesto"
        aria-labelledby="about-title"
      >
        <Reveal className={cx("editorial-copy")}>
          <div />
          <div>
            {store ? (
              <h2 id="about-title">{store.about_title}</h2>
            ) : (
              <Skeleton kind="title" />
            )}
            {store ? (
              <p>{store.about_text}</p>
            ) : (
              <>
                <Skeleton />
                <Skeleton />
                <Skeleton />
              </>
            )}
            <Link to="/catalog">Посмотреть коллекцию</Link>
          </div>
        </Reveal>
        <div className={cx("editorial-image")}>
          {store ? (
            <SmartImage
              key={store.about_image}
              src={store.about_image}
              alt="Лаконичный силуэт коллекции ATELIER NOIR"
            />
          ) : (
            <Skeleton kind="fill" />
          )}
        </div>
      </section>
      <section
        className={cx("delivery-section", "shell")}
        aria-labelledby="delivery-title"
      >
        <Reveal>
          <h2 id="delivery-title">
            Покупки без
            <br />
            лишних шагов.
          </h2>
          <p>
            Выбирайте вещь, размер и цвет. Добавляйте покупки в корзину,
            применяйте промокод и выбирайте удобный способ получения.
          </p>
          <Link className={cx("link-btn")} to="/delivery">
            Подробнее о доставке и оплате
          </Link>
        </Reveal>
        <Reveal className={cx("details-list")}>
          <article>
            <strong>Ваша посадка</strong>
            <p>
              Размер и цвет выбираются отдельно для каждой вещи. Доступное
              количество видно сразу.
            </p>
          </article>
          <article>
            <strong>Доставка СДЭК</strong>
            <p>
              В пункт выдачи или курьером. Стоимость и срок рассчитываются при
              оформлении.
            </p>
          </article>
          <article>
            <strong>Оплата онлайн</strong>
            <p>Переход к оплате после проверки состава и суммы заказа.</p>
          </article>
          <article>
            <strong>На связи</strong>
            <p>
              Подтверждение заказа и оплаты придёт на вашу электронную почту.
            </p>
          </article>
        </Reveal>
      </section>
    </>
  );
}
