import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { useResource } from "../hooks/useResource";
import { useStore } from "../app/StoreContext";
import { PageSkeleton } from "../components/Skeleton";
import { cx, ErrorState } from "../components/ui";
export function ContentPage({ page }: { page?: string }) {
  const { slug } = useParams();
  const resource = useResource<{
    title: string;
    description: string;
    body: string;
  }>("/pages/" + (page ?? slug) + "/");
  useEffect(() => {
    if (resource.data) {
      document.title = resource.data.title + " · ATELIER NOIR";
      document
        .querySelector('meta[name="description"]')
        ?.setAttribute("content", resource.data.description);
    }
  }, [resource.data]);
  return (
    <section className={cx("content-page", "shell")}>
      {resource.loading ? (
        <PageSkeleton />
      ) : resource.error ? (
        <ErrorState error={resource.error} retry={resource.retry} />
      ) : (
        resource.data && (
          <>
            <h1>{resource.data.title}</h1>
            <div className={cx("prose")}>
              {resource.data.body
                .split("\n\n")
                .filter(Boolean)
                .map((text, i) => (
                  <p key={i}>{text}</p>
                ))}
            </div>
            <Link className={cx("back-link")} to="/#catalog">
              К коллекции
            </Link>
          </>
        )
      )}
    </section>
  );
}
export function ContactsPage() {
  const { data: store, loading, error, retry } = useStore();
  useEffect(() => {
    document.title = "Контакты · ATELIER NOIR";
  }, []);
  return (
    <section className={cx("content-page", "shell")}>
      {loading ? (
        <PageSkeleton />
      ) : error ? (
        <ErrorState error={error} retry={retry} />
      ) : (
        store && (
          <>
            <h1>Будем на связи.</h1>
            <div className={cx("prose")}>
              <p>Поможем с выбором размера, оформлением и получением заказа.</p>
              <p>
                <a href={"mailto:" + store.email}>{store.email}</a>
                {store.phone && (
                  <>
                    <br />
                    <a href={"tel:" + store.phone.replace(/[^+\d]/g, "")}>
                      {store.phone}
                    </a>
                  </>
                )}
              </p>
              {store.address && <p>{store.address}</p>}
              {store.legal_details && <p>{store.legal_details}</p>}
            </div>
          </>
        )
      )}
    </section>
  );
}
export function NotFound() {
  useEffect(() => {
    document.title = "Страница не найдена · ATELIER NOIR";
  }, []);
  return (
    <section className={cx("content-page", "shell")}>
      <h1>Здесь пока тихо.</h1>
      <p>Страница не найдена. Возможно, адрес изменился.</p>
      <Link className={cx("primary-btn")} to="/">
        На главную
      </Link>
    </section>
  );
}
