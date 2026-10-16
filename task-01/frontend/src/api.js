const BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

// Demo identity: one random "till" id per browser. Header is sent on every call.
export const userId =
  localStorage.getItem("pos_user") ||
  (() => {
    const id = "till-" + Math.random().toString(36).slice(2, 8);
    localStorage.setItem("pos_user", id);
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
