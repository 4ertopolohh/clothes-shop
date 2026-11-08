import { createContext, useContext, type ReactNode } from "react";
import { useResource } from "../hooks/useResource";
import type { Store } from "../types";
const Context = createContext<ReturnType<typeof useResource<Store>> | null>(
  null,
);
export function StoreProvider({ children }: { children: ReactNode }) {
  const store = useResource<Store>("/settings/");
  return <Context.Provider value={store}>{children}</Context.Provider>;
}
export function useStore() {
  const value = useContext(Context);
  if (!value) throw new Error("StoreProvider");
  return value;
}
