import { useState, useSyncExternalStore } from "react";
import s from "./Skeleton.module.scss";
import { network } from "../api/client";
export function Skeleton({
  kind = "text",
  className = "",
}: {
  kind?: "text" | "title" | "photo" | "block" | "fill";
  className?: string;
}) {
  return (
    <span aria-hidden="true" className={`${s.shape} ${s[kind]} ${className}`} />
  );
}
export function CatalogSkeleton() {
  return (
    <div className={s.grid} role="status" aria-label="Загружаем коллекцию">
      {Array.from({ length: 6 }, (_, i) => (
        <div key={i}>
          <Skeleton kind="photo" />
          <Skeleton />
          <Skeleton />
        </div>
      ))}
    </div>
  );
}
export function PageSkeleton() {
  return (
    <div role="status" aria-label="Загружаем страницу">
      <Skeleton kind="title" />
      {Array.from({ length: 5 }, (_, i) => (
        <Skeleton key={i} />
      ))}
      <Skeleton kind="block" />
    </div>
  );
}
export function SiteLoader() {
  const active =
    useSyncExternalStore(network.subscribe, network.snapshot, () => 0) > 0;
  return active ? (
    <div className={s.loader} role="progressbar" aria-label="Загрузка" />
  ) : null;
}
export function Spinner() {
  return <span className={s.spinner} aria-hidden="true" />;
}
export function SmartImage({
  src,
  alt,
  eager = false,
}: {
  src: string;
  alt: string;
  eager?: boolean;
}) {
  const [loaded, setLoaded] = useState(false),
    [failed, setFailed] = useState(!src);
  return (
    <span className={s.media}>
      {!loaded && !failed && <Skeleton kind="fill" />}
      {failed ? (
        <span className={s.failure}>Фотография временно недоступна</span>
      ) : (
        <img
          className={loaded ? "" : s.hidden}
          src={src}
          alt={alt}
          loading={eager ? "eager" : "lazy"}
          fetchPriority={eager ? "high" : "auto"}
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
        />
      )}
    </span>
  );
}
