import {
  useEffect,
  useRef,
  useId,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import styles from "../styles/Shop.module.scss";
import { createPortal } from "react-dom";
let drawerCount = 0;
let savedOverflow = "";
export const cx = (...names: (string | false | undefined)[]) =>
  names
    .filter(Boolean)
    .map((n) => styles[n as string] ?? n)
    .join(" ");
export const fmt = (value: string | number) =>
  new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "RUB",
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(Number(value));
export function itemCount(count: number) {
  const mod100 = count % 100,
    mod10 = count % 10;
  return `${count} ${mod100 >= 11 && mod100 <= 14 ? "вещей" : mod10 === 1 ? "вещь" : mod10 >= 2 && mod10 <= 4 ? "вещи" : "вещей"}`;
}
export function ErrorState({
  error,
  retry,
}: {
  error: Error | string;
  retry?: () => void;
}) {
  return (
    <div className={cx("error-state")} role="alert">
      <p>{typeof error === "string" ? error : error.message}</p>
      {retry && (
        <button className={cx("outline-btn")} onClick={retry}>
          Попробовать ещё раз
        </button>
      )}
    </div>
  );
}
export function Select({
  label,
  value,
  options,
  onChange,
  disabled = false,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const wrapper = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const close = (e: PointerEvent) => {
      if (!wrapper.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);
  return (
    <div className={cx("select", open && "open")} ref={wrapper}>
      <button
        type="button"
        className={cx("select-trigger")}
        disabled={disabled}
        aria-label={label}
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((x) => !x)}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setOpen(true);
            setTimeout(
              () =>
                wrapper.current
                  ?.querySelector<HTMLButtonElement>("[role=option]")
                  ?.focus(),
              0,
            );
          }
        }}
      >
        {options.find((o) => o.value === value)?.label ?? label}
      </button>
      {open && (
        <div
          className={cx("select-options")}
          id={id}
          role="listbox"
          aria-label={label}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              setOpen(false);
              wrapper.current?.querySelector("button")?.focus();
            }
            const nodes = Array.from(
              wrapper.current?.querySelectorAll<HTMLButtonElement>(
                "[role=option]",
              ) ?? [],
            );
            const index = nodes.indexOf(
              document.activeElement as HTMLButtonElement,
            );
            if (e.key === "ArrowDown" || e.key === "ArrowUp") {
              e.preventDefault();
              nodes[
                (index + (e.key === "ArrowDown" ? 1 : -1) + nodes.length) %
                  nodes.length
              ]?.focus();
            }
            if (e.key === "Home") {
              e.preventDefault();
              nodes[0]?.focus();
            }
            if (e.key === "End") {
              e.preventDefault();
              nodes.at(-1)?.focus();
            }
          }}
        >
          {options.map((option) => (
            <button
              type="button"
              role="option"
              aria-selected={value === option.value}
              className={cx(
                "select-option",
                value === option.value && "selected",
              )}
              key={option.value}
              onClick={() => {
                onChange(option.value);
                setOpen(false);
                wrapper.current?.querySelector("button")?.focus();
              }}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
export function Drawer({
  title,
  children,
  onClose,
  wide = false,
  fullscreen = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
  fullscreen?: boolean;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const [closing, setClosing] = useState(false);
  const closingRef = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const callback = useRef(onClose);
  callback.current = onClose;
  const requestClose = () => {
    if (closingRef.current) return;
    closingRef.current = true;
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
      callback.current();
      return;
    }
    setClosing(true);
    timer.current = setTimeout(() => callback.current(), 300);
  };
  const close = useRef(requestClose);
  close.current = requestClose;
  useEffect(() => () => clearTimeout(timer.current), []);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    if (drawerCount === 0) savedOverflow = document.body.style.overflow;
    drawerCount++;
    const root = document.getElementById("root");
    if (root) root.inert = true;
    document.body.style.overflow = "hidden";
    const focusFrame = requestAnimationFrame(() =>
      panel.current
        ?.querySelector<HTMLElement>('button,a,input,[tabindex="0"]')
        ?.focus(),
    );
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") close.current();
      if (e.key === "Tab") {
        const nodes = Array.from(
          panel.current?.querySelectorAll<HTMLElement>(
            'a[href],button:not(:disabled),input:not(:disabled),textarea,[tabindex="0"]',
          ) ?? [],
        ).filter((n) => n.getClientRects().length);
        const first = nodes[0],
          last = nodes.at(-1);
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      cancelAnimationFrame(focusFrame);
      drawerCount--;
      if (drawerCount === 0) {
        document.body.style.overflow = savedOverflow;
        if (root) root.inert = false;
        previous?.focus();
      }
      document.removeEventListener("keydown", key);
    };
  }, []);
  const id = useId();
  return createPortal(
    <div
      className={cx("overlay", closing && "closing")}
      onClick={(e) => {
        if (e.target === e.currentTarget) requestClose();
      }}
    >
      <div
        ref={panel}
        className={cx(
          "panel",
          wide && "wide-panel",
          fullscreen && "fullscreen-panel",
        )}
        role="dialog"
        aria-modal="true"
        aria-labelledby={id}
      >
        <div className={cx("panel-head")}>
          <h2 id={id}>{title}</h2>
          <button
            className={cx("close-btn")}
            onClick={requestClose}
            aria-label="Закрыть панель"
          >
            Закрыть
          </button>
        </div>
        <div className={cx("panel-body")}>{children}</div>
      </div>
    </div>,
    document.body,
  );
}
type RevealVariant =
  | "fade-up"
  | "fade-down"
  | "fade-left"
  | "fade-right"
  | "scale-in"
  | "image-reveal"
  | "stagger";
const observers = new Map<
  number,
  {
    observer: IntersectionObserver;
    callbacks: Map<Element, (entry: IntersectionObserverEntry) => void>;
  }
>();
export function Reveal({
  children,
  className = "",
  variant = "fade-up",
  duration = 750,
  delay = 0,
  threshold = 0.12,
  once = true,
}: {
  children: ReactNode;
  className?: string;
  variant?: RevealVariant;
  duration?: number;
  delay?: number;
  threshold?: number;
  once?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = ref.current;
    if (!node || !("IntersectionObserver" in window)) return;
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    if (media.matches) return;
    const level = Math.max(0, Math.min(1, threshold));
    let pool = observers.get(level);
    if (!pool) {
      const callbacks = new Map<
        Element,
        (entry: IntersectionObserverEntry) => void
      >();
      const observer = new IntersectionObserver(
        (entries) =>
          entries.forEach((entry) => callbacks.get(entry.target)?.(entry)),
        { threshold: level },
      );
      pool = { observer, callbacks };
      observers.set(level, pool);
    }
    const current = pool;
    const release = () => {
      current.observer.unobserve(node);
      current.callbacks.delete(node);
      if (!current.callbacks.size) {
        current.observer.disconnect();
        if (observers.get(level) === current) observers.delete(level);
      }
    };
    current.callbacks.set(node, (entry) => {
      if (entry.isIntersecting) {
        node.dataset.shown = "true";
        if (once) release();
      } else if (
        !once &&
        (entry.boundingClientRect.bottom < -80 ||
          entry.boundingClientRect.top > innerHeight + 80)
      )
        node.dataset.shown = "false";
    });
    current.observer.observe(node);
    node.dataset.ready = "true";
    const show = () => {
      if (media.matches) {
        delete node.dataset.ready;
        release();
      }
    };
    media.addEventListener("change", show);
    return () => {
      release();
      media.removeEventListener("change", show);
      delete node.dataset.ready;
    };
  }, [threshold, once]);
  return (
    <div
      ref={ref}
      data-variant={variant}
      className={`${cx("reveal")} ${className}`}
      style={
        {
          "--reveal-duration": `${duration}ms`,
          "--reveal-delay": `${delay}ms`,
        } as CSSProperties
      }
    >
      {children}
    </div>
  );
}
export function Logo({
  variant = "header",
}: {
  variant?: "header" | "footer" | "hero";
}) {
  return (
    <img
      className={cx("logo", `logo-${variant}`)}
      src="/project-logo-02-2048.png"
      alt={variant === "hero" ? "" : "ATELIER NOIR"}
      width="2048"
      height="2048"
    />
  );
}
