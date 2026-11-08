import { useEffect, useState } from "react";
import { request } from "../api/client";
import { usePreloaded } from "../app/PublicData";
export function useResource<T>(path: string) {
  const initial = usePreloaded<T>(path);
  const [state, setState] = useState<{
    path: string;
    data?: T;
    error?: Error;
    loading: boolean;
  }>({ path, data: initial, loading: !initial });
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const control = new AbortController();
    setState((previous) =>
      previous.path === path && previous.data
        ? { ...previous, error: undefined }
        : { path, data: initial, loading: !initial },
    );
    request<T>(path, { signal: control.signal })
      .then((data) => setState({ path, data, loading: false }))
      .catch((e: Error) => {
        if (e.name !== "AbortError")
          setState({ path, error: e, loading: false });
      });
    return () => control.abort();
  }, [path, version]);
  return {
    ...(state.path === path
      ? state
      : { path, data: initial, loading: !initial }),
    retry: () => setVersion((x) => x + 1),
  };
}
