let pending = 0;
const listeners = new Set<() => void>();
export const network = {
  subscribe: (fn: () => void) => {
    listeners.add(fn);
    return () => {
      listeners.delete(fn);
    };
  },
  snapshot: () => pending,
};
function update(delta: number) {
  pending += delta;
  listeners.forEach((fn) => fn());
}
export class ApiError extends Error {
  constructor(
    public status: number,
    public details: unknown,
  ) {
    super(errorMessage(details));
  }
}
export function errorMessage(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(errorMessage).join(" ");
  if (value && typeof value === "object")
    return Object.values(value).map(errorMessage).join(" ");
  return "Не удалось выполнить запрос. Попробуйте ещё раз.";
}
let csrf: Promise<string> | undefined;
async function token() {
  return (csrf ??= request<{ csrfToken: string }>("/csrf/")
    .then((x) => x.csrfToken)
    .catch((e) => {
      csrf = undefined;
      throw e;
    }));
}
export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  update(1);
  try {
    const response = await fetch("/api" + path, {
      ...options,
      credentials: "same-origin",
      headers: { Accept: "application/json", ...options.headers },
    });
    const data: unknown = await response
      .json()
      .catch(() => ({ detail: "Сервер временно недоступен." }));
    if (!response.ok) throw new ApiError(response.status, data);
    return data as T;
  } finally {
    update(-1);
  }
}
export async function post<T>(
  path: string,
  body: unknown = {},
  signal?: AbortSignal,
): Promise<T> {
  const csrfToken = await token();
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
    body: JSON.stringify(body),
    signal,
  });
}
