import { createContext, useContext, type ReactNode } from "react";
export type PublicData = Record<string, unknown>;
const Context = createContext<PublicData>({});
export function PublicDataProvider({
  data,
  children,
}: {
  data: PublicData;
  children: ReactNode;
}) {
  return <Context.Provider value={data}>{children}</Context.Provider>;
}
export function usePreloaded<T>(path: string): T | undefined {
  return useContext(Context)[path] as T | undefined;
}
