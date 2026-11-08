import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import type { CartLine, Product, Variant } from "../../types";
interface CartState {
  lines: CartLine[];
  open: boolean;
  setOpen: (v: boolean) => void;
  add: (p: Product, v: Variant, q: number) => void;
  quantity: (id: number, q: number) => void;
  remove: (id: number) => void;
  clear: () => void;
  promo: string;
  setPromo: (v: string) => void;
  toast: string;
  notify: (text: string) => void;
}
const Context = createContext<CartState | null>(null);
function saved(): CartLine[] {
  try {
    const value: unknown = JSON.parse(
      localStorage.getItem("an-cart-v2") ?? "[]",
    );
    if (!Array.isArray(value)) return [];
    return (value as CartLine[])
      .filter(
        (x) =>
          x &&
          Number.isInteger(x.variant_id) &&
          x.quantity > 0 &&
          x.quantity <= 30 &&
          x.product &&
          typeof x.product.slug === "string" &&
          Array.isArray(x.product.variants) &&
          Array.isArray(x.product.images),
      )
      .slice(0, 50);
  } catch {
    return [];
  }
}
export function CartProvider({ children }: { children: ReactNode }) {
  const [lines, setLines] = useState<CartLine[]>(saved),
    [open, setOpen] = useState(false),
    [promo, setPromo] = useState(""),
    [toast, setToast] = useState("");
  useEffect(() => {
    try {
      localStorage.setItem("an-cart-v2", JSON.stringify(lines));
    } catch {
      /* Private browsing can disable storage. */
    }
  }, [lines]);
  useEffect(() => {
    if (!toast) return;
    const timeout = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(timeout);
  }, [toast]);
  const notify = useCallback((text: string) => setToast(text), []);
  const add = (product: Product, variant: Variant, quantity: number) => {
    setLines((current) => {
      const existing = current.find((x) => x.variant_id === variant.id);
      const count = Math.min(
        variant.available,
        30,
        (existing?.quantity ?? 0) + quantity,
      );
      return existing
        ? current.map((x) =>
            x.variant_id === variant.id
              ? { ...x, quantity: count, product }
              : x,
          )
        : [...current, { variant_id: variant.id, quantity: count, product }];
    });
    notify("Вещь добавлена в корзину");
  };
  return (
    <Context.Provider
      value={{
        lines,
        open,
        setOpen,
        add,
        quantity: (id, q) =>
          setLines((xs) =>
            xs.map((x) =>
              x.variant_id === id
                ? { ...x, quantity: Math.max(1, Math.min(30, q)) }
                : x,
            ),
          ),
        remove: (id) => setLines((xs) => xs.filter((x) => x.variant_id !== id)),
        clear: () => {
          setLines([]);
          setPromo("");
        },
        promo,
        setPromo,
        toast,
        notify,
      }}
    >
      {children}
    </Context.Provider>
  );
}
export function useCart() {
  const value = useContext(Context);
  if (!value) throw new Error("CartProvider");
  return value;
}
