const BASE = (import.meta.env.VITE_API_URL || "http://localhost:8001").replace(/\/$/, "");

// Demo identity: one random shopper id per browser. Header is sent on every call.
export const userId =
  localStorage.getItem("shop_user") ||
  (() => {
    const id = "shopper-" + Math.random().toString(36).slice(2, 8);
    localStorage.setItem("shop_user", id);
    return id;
  })();

export async function api(path, { method = "GET", body, headers = {} } = {}) {
  const res = await fetch(BASE + path, {
    method,
    headers: { "Content-Type": "application/json", "X-User-Id": userId, ...headers },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
  return data;
}

// List call that also returns the total number of matches (X-Total-Count header) for pagination.
export async function apiList(path, { signal } = {}) {
  const res = await fetch(BASE + path, { headers: { "X-User-Id": userId }, signal });
  const data = await res.json().catch(() => []);
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Could not load products");
  return { items: data, total: Number(res.headers.get("X-Total-Count") || data.length) };
}
