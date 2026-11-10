import { ProductCard } from "./ProductCard";
import { useEffect, useState, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { request } from "../../api/client";
import { useResource } from "../../hooks/useResource";
import { usePreloaded } from "../../app/PublicData";
import type { CatalogResponse, Facets } from "../../types";
import {
  cx,
  Select,
  Reveal,
  ErrorState,
  fmt,
  Drawer,
  itemCount,
} from "../../components/ui";
import { Skeleton, CatalogSkeleton, Spinner } from "../../components/Skeleton";

export function Catalog() {
  const [params, setParams] = useSearchParams();
  const initial = usePreloaded<CatalogResponse>("/catalog/?&page=1");
  const facets = useResource<Facets>("/catalog/facets/");
  const [mobile, setMobile] = useState(false);
  const [page, setPage] = useState(1),
    [result, setResult] = useState<CatalogResponse | undefined>(
      params.size === 0 ? initial : undefined,
    ),
    [loading, setLoading] = useState(!initial || params.size > 0),
    [error, setError] = useState<Error>(),
    [revision, setRevision] = useState(0);
  const key = params.toString();
  const previousKey = useRef(key);
  useEffect(() => {
    if (previousKey.current === key) return;
    previousKey.current = key;
    setPage(1);
    setResult(undefined);
  }, [key]);
  useEffect(() => {
    const abort = new AbortController();
    setLoading(true);
    setError(undefined);
    request<CatalogResponse>("/catalog/?" + key + "&page=" + page, {
      signal: abort.signal,
    })
      .then((data) => {
        setResult((old) =>
          page > 1 && old
            ? {
                ...data,
                results: [
                  ...old.results,
                  ...data.results.filter(
                    (p) => !old.results.some((x) => x.id === p.id),
                  ),
                ],
              }
            : data,
        );
        setLoading(false);
      })
      .catch((e: Error) => {
        if (e.name !== "AbortError") {
          setError(e);
          setLoading(false);
        }
      });
    return () => abort.abort();
  }, [key, page, revision]);
  const update = (name: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(name, value);
    else next.delete(name);
    setPage(1);
    setParams(next, { preventScrollReset: true });
  };
  const toggle = (name: string, value: string) => {
    const selected = (params.get(name) ?? "").split(",").filter(Boolean);
    update(
      name,
      selected.includes(value)
        ? selected.filter((x) => x !== value).join(",")
        : [...selected, value].join(","),
    );
  };
  const active = (name: string, value: string) =>
    (params.get(name) ?? "").split(",").includes(value);
  const filterContent = (
    <>
      {facets.loading ? (
        <>
          <Skeleton kind="block" />
          <Skeleton kind="block" />
        </>
      ) : facets.error ? (
        <ErrorState error={facets.error} retry={facets.retry} />
      ) : (
        facets.data && (
          <>
            <div className={cx("filter-group")}>
              <h3 className={cx("filter-title")}>Категория</h3>
              {facets.data.categories.map((c) => (
                <label className={cx("filter-check")} key={c.slug}>
                  <input
                    type="checkbox"
                    checked={active("category", c.slug)}
                    onChange={() => toggle("category", c.slug)}
                  />
                  <span>{c.name}</span>
                </label>
              ))}
            </div>
            <div className={cx("filter-group")}>
              <h3 className={cx("filter-title")}>Размер</h3>
              <div className={cx("size-options")}>
                {[...facets.data.sizes]
                  .sort(
                    (a, b) =>
                      ["XS", "S", "M", "L", "XL", "XXL"].indexOf(a) -
                      ["XS", "S", "M", "L", "XL", "XXL"].indexOf(b),
                  )
                  .map((size) => (
                    <label
                      key={size}
                      className={cx(
                        "size-chip",
                        active("size", size) && "selected",
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={active("size", size)}
                        onChange={() => toggle("size", size)}
                      />
                      <span>{size}</span>
                    </label>
                  ))}
              </div>
            </div>
            <div className={cx("filter-group")}>
              <h3 className={cx("filter-title")}>Цвет</h3>
              <div className={cx("color-options")}>
                {facets.data.colors.map((c) => (
                  <button
                    key={c.color}
                    className={cx(
                      "swatch",
                      active("color", c.color) && "active",
                    )}
                    style={{ background: c.color_hex }}
                    title={c.color}
                    aria-label={"Цвет: " + c.color}
                    aria-pressed={active("color", c.color)}
                    onClick={() => toggle("color", c.color)}
                  />
                ))}
              </div>
            </div>
            <div className={cx("filter-group")}>
              <h3 className={cx("filter-title")}>
                Цена{" "}
                <span className={cx("filter-count")}>
                  до {fmt(params.get("max_price") ?? facets.data.max_price)}
                </span>
              </h3>
              <input
                className={cx("range-input")}
                type="range"
                min="0"
                max={facets.data.max_price}
                value={params.get("max_price") ?? facets.data.max_price}
                step="500"
                aria-label="Максимальная цена"
                onChange={(e) => update("max_price", e.target.value)}
              />
            </div>
            <label className={cx("filter-check")}>
              <input
                type="checkbox"
                checked={params.get("new") === "1"}
                onChange={(e) => update("new", e.target.checked ? "1" : "")}
              />
              <span>Только новинки</span>
            </label>
          </>
        )
      )}
      <div className={cx("filters-bottom")}>
        <button
          className={cx("link-btn")}
          onClick={() => {
            setPage(1);
            setParams({});
          }}
        >
          Сбросить все фильтры
        </button>
      </div>
    </>
  );
  return (
    <section
      id="catalog"
      className={cx("catalog-section", "shell")}
      aria-labelledby="catalog-title"
    >
      <Reveal className={cx("catalog-heading")}>
        <h2 id="catalog-title" className={cx("section-title")}>
          Коллекция
        </h2>
        <div className={cx("catalog-lead")}>
          Создано для движения и повседневных ритуалов. Выбирайте вещи по
          силуэту, размеру и оттенку.
        </div>
      </Reveal>
      <div className={cx("catalog-layout")}>
        <aside className={cx("filters")} aria-label="Фильтры товаров">
          {filterContent}
        </aside>
        <div>
          <div className={cx("catalog-tools")}>
            <button
              className={cx("mobile-filter-btn")}
              onClick={() => setMobile(true)}
              aria-expanded={mobile}
            >
              Фильтры
            </button>
            <span className={cx("catalog-meta")} aria-live="polite">
              {result ? itemCount(result.count) : <Skeleton />}
            </span>
            <div className={cx("sort-area")}>
              <span>Сортировать:</span>
              <Select
                label="Сортировка"
                value={params.get("sort") ?? "default"}
                options={[
                  { value: "default", label: "По умолчанию" },
                  { value: "price_asc", label: "Сначала дешевле" },
                  { value: "price_desc", label: "Сначала дороже" },
                  { value: "new", label: "Сначала новинки" },
                ]}
                onChange={(v) => update("sort", v)}
              />
            </div>
          </div>
          {params.get("q") && <p>Поиск: «{params.get("q")}»</p>}
          {error && (
            <ErrorState error={error} retry={() => setRevision((x) => x + 1)} />
          )}
          <div aria-busy={loading}>
            {loading && page === 1 && !result ? (
              <CatalogSkeleton />
            ) : result?.results.length ? (
              <div className={cx("products")}>
                {result.results.map((product, index) => (
                  <ProductCard
                    product={product}
                    index={index}
                    key={product.id}
                  />
                ))}
              </div>
            ) : (
              !error && (
                <div className={cx("no-results")}>
                  <p>Пока нет вещей с такими параметрами.</p>
                  <button
                    className={cx("outline-btn")}
                    onClick={() => setParams({})}
                  >
                    Сбросить фильтры
                  </button>
                </div>
              )
            )}
          </div>
          {result?.next && (
            <button
              className={cx("show-more")}
              disabled={loading}
              onClick={() => setPage(result.next!)}
            >
              {loading && <Spinner />}Показать ещё
            </button>
          )}
        </div>
      </div>
      {mobile && (
        <Drawer title="Фильтры" onClose={() => setMobile(false)}>
          {filterContent}
          <button
            className={cx("primary-btn", "full")}
            onClick={() => setMobile(false)}
          >
            Показать вещи
          </button>
        </Drawer>
      )}
    </section>
  );
}
