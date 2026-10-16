import { useCallback, useEffect, useRef, useState } from "react";
import { api, apiList, userId } from "./api";

const money = (n) => `$${Number(n).toFixed(2)}`;
const PAGE_SIZE = 10;
const MAX_PRICE = 25;
const HIDDEN_PRODUCT_NAMES = new Set(["Concurrency test item"]);
const SORTS = [["newest", "Newest"], ["price_asc", "Price: Low to High"], ["price_desc", "Price: High to Low"], ["name", "Name A-Z"]];
const DEFAULT_FILTERS = { search: "", category: "", min: 0, max: MAX_PRICE, in_stock: false, sort: "newest", page: 1 };

/* ------------------------------ small pieces ----------------------------- */
const CartIcon = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <circle cx="9" cy="20" r="1.5" /><circle cx="18" cy="20" r="1.5" /><path d="M2 3h3l2.6 12.2a2 2 0 0 0 2 1.6h7.8a2 2 0 0 0 2-1.5L21 8H6" />
  </svg>
);
const SearchIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
);
const Logo = () => (
  <svg width="46" height="40" viewBox="0 0 46 40" aria-hidden="true">
    <path d="M3 8c7-2 13-1 20 3v26c-7-4-13-5-20-3z" fill="#0b72b5" /><path d="M43 8c-7-2-13-1-20 3v26c7-4 13-5 20-3z" fill="#095a91" />
    <path d="M8 13c5-1 9 0 12 2M8 19c5-1 9 0 12 2M26 15c3-2 7-3 12-2M26 21c3-2 7-3 12-2" stroke="#fff" strokeWidth="1.6" fill="none" strokeLinecap="round" />
  </svg>
);

function Pic({ p, className = "" }) {
  const [bad, setBad] = useState(false);
  if (!p.image_url || bad) {
    return <div className={`pic placeholder ${className}`} aria-hidden="true">{p.name[0]}</div>;
  }
  return <img className={`pic ${className}`} src={p.image_url} alt={p.name} loading="lazy" onError={() => setBad(true)} />;
}
const stockInfo = (p) =>
  p.available === 0 ? ["out", "Out of stock"] : p.available <= 3 ? ["low", `Only ${p.available} left`] : ["in", "In stock"];

function DualRange({ lo, hi, onChange }) {
  return (
    <div className="dual">
      <div className="track"><div className="fill" style={{ left: `${(lo / MAX_PRICE) * 100}%`, right: `${100 - (hi / MAX_PRICE) * 100}%` }} /></div>
      <input type="range" min="0" max={MAX_PRICE} value={lo} aria-label="Minimum price" onChange={(e) => onChange(Math.min(Number(e.target.value), hi), hi)} />
      <input type="range" min="0" max={MAX_PRICE} value={hi} aria-label="Maximum price" onChange={(e) => onChange(lo, Math.max(Number(e.target.value), lo))} />
    </div>
  );
}

function Pagination({ page, total, onPage }) {
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (pages <= 1) return null;
  return (
    <nav className="pager" aria-label="Pagination">
      <button disabled={page === 1} onClick={() => onPage(page - 1)} aria-label="Previous page">‹</button>
      {Array.from({ length: pages }, (_, i) => i + 1).map((n) => (
        <button key={n} className={n === page ? "on" : ""} aria-current={n === page ? "page" : undefined} onClick={() => onPage(n)}>{n}</button>
      ))}
      <button disabled={page === pages} onClick={() => onPage(page + 1)} aria-label="Next page">›</button>
    </nav>
  );
}

/* ------------------------------- Home / list ------------------------------ */
function Filters({ f, update, cats }) {
  const setMin = (v) => update({ min: Math.max(0, Math.min(Number(v) || 0, f.max)) });
  const setMax = (v) => update({ max: Math.min(MAX_PRICE, Math.max(Number(v) || 0, f.min)) });
  return (
    <aside className="side">
      <div className="box">
        <h3>Search</h3>
        <label className="field icon"><SearchIcon /><input type="search" placeholder="Search products..." value={f.search} onChange={(e) => update({ search: e.target.value })} /></label>
        <h3>Category</h3>
        <select value={f.category} onChange={(e) => update({ category: e.target.value })} aria-label="Category">
          <option value="">All categories</option>{cats.map((c) => <option key={c}>{c}</option>)}
        </select>
        <h3>Price Range</h3>
        <div className="minmax">
          <label>Min: ${f.min}<input type="number" min="0" max={MAX_PRICE} value={f.min} onChange={(e) => setMin(e.target.value)} /></label>
          <label>Max: ${f.max}<input type="number" min="0" max={MAX_PRICE} value={f.max} onChange={(e) => setMax(e.target.value)} /></label>
        </div>
        <DualRange lo={f.min} hi={f.max} onChange={(min, max) => update({ min, max })} />
        <h3>In Stock Only</h3>
        <label className="check"><input type="checkbox" checked={f.in_stock} onChange={(e) => update({ in_stock: e.target.checked })} /> In stock only</label>
        <h3>Sort by</h3>
        <select value={f.sort} onChange={(e) => update({ sort: e.target.value })} aria-label="Sort by">
          {SORTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        {(f.search || f.category || f.in_stock || f.min > 0 || f.max < MAX_PRICE) && (
          <button className="clear" onClick={() => update({ ...DEFAULT_FILTERS, sort: f.sort })}>Clear filters</button>
        )}
      </div>
      <div className="promo">
        <div><b>Get Ready<br />for a Better<br />Tomorrow</b><p>Quality school supplies for every student.</p></div>
        <svg width="96" height="96" viewBox="0 0 96 96" aria-hidden="true">
          <rect x="14" y="70" width="70" height="10" rx="2" fill="#2563eb" /><rect x="20" y="60" width="60" height="10" rx="2" fill="#e11d48" />
          <rect x="30" y="34" width="30" height="26" rx="4" fill="#1d4ed8" />
          {["#ef4444", "#facc15", "#22c55e", "#a855f7"].map((c, i) => <rect key={i} x={33 + i * 6} y={14 + (i % 2) * 5} width="4" height="24" fill={c} />)}
        </svg>
      </div>
    </aside>
  );
}

function Shop({ f, update, open, addToCart, cart }) {
  const [cats, setCats] = useState([]);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api("/products/categories").then(setCats).catch(() => {}); }, []);
  useEffect(() => {
    const qs = new URLSearchParams({ page: f.page, page_size: PAGE_SIZE, sort: f.sort });
    if (f.search.trim()) qs.set("search", f.search.trim());
    if (f.category) qs.set("category", f.category);
    if (f.min > 0) qs.set("min_price", f.min);
    if (f.max < MAX_PRICE) qs.set("max_price", f.max);
    if (f.in_stock) qs.set("in_stock", "true");
    const controller = new AbortController();
    const t = setTimeout(() => apiList(`/products?${qs}`, { signal: controller.signal })
      .then((d) => { setData(d); setError(""); })
      .catch((e) => { if (e.name !== "AbortError") setError(e.message); }), 250);
    return () => { clearTimeout(t); controller.abort(); }; // debounce and discard stale results
  }, [f]);

  const visibleProducts = (data?.items || []).filter((p) => !HIDDEN_PRODUCT_NAMES.has(p.name));
  const visibleTotal = data ? Math.max(0, data.total - (data.items.length - visibleProducts.length)) : 0;

  return (
    <div className="layout">
      <Filters f={f} update={update} cats={cats} />
      <section>
        <div className="head">
          <h1>School Accessories</h1>
          <select value={f.sort} onChange={(e) => update({ sort: e.target.value })} aria-label="Sort products">
            {SORTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        {error && <p className="err" role="alert">{error}</p>}
        {!data && !error && <p className="muted">Loading products...</p>}
        {data && visibleProducts.length === 0 && <p className="muted empty">No products match these filters. Try clearing the search or widening the price range.</p>}
        <div className="grid">
          {visibleProducts.map((p) => {
            const [cls, label] = stockInfo(p);
            const inCart = cart.items.find((i) => i.product_id === p.id)?.qty || 0;
            return (
              <article className="card" key={p.id}>
                <button className="imgbtn" onClick={() => open(p.id)} aria-label={`View ${p.name}`}><Pic p={p} /></button>
                <h2><button className="plain" onClick={() => open(p.id)}>{p.name}</button></h2>
                <p className="price">{money(p.price)}</p>
                <p className={`stock ${cls}`}><span className="dot" />{label}{inCart > 0 && <em> · {inCart} in cart</em>}</p>
                <button className="add" disabled={p.available <= inCart} onClick={() => addToCart(p)}><CartIcon /> {p.available === 0 ? "Out of stock" : "Add to Cart"}</button>
              </article>
            );
          })}
        </div>
        {data && <Pagination page={f.page} total={visibleTotal} onPage={(page) => update({ page })} />}
      </section>
    </div>
  );
}

/* ----------------------------- Product details ---------------------------- */
function Product({ id, back, addToCart, notify }) {
  const [p, setP] = useState(null);
  const [qty, setQty] = useState(1);
  useEffect(() => { api(`/products/${id}`).then(setP).catch((e) => notify(e.message, true)); }, [id]);
  if (!p) return <p className="muted">Loading...</p>;
  const [cls, label] = stockInfo(p);
  return (
    <div className="panel">
      <button className="link" onClick={back}>‹ Back to products</button>
      <div className="detail">
        <Pic p={p} className="bigpic" />
        <div className="info">
          <h1>{p.name}</h1>
          <p className="price big">{money(p.price)}</p>
          <p>{p.description || "No description provided."}</p>
          <p className="muted">Category: {p.category || "Uncategorised"}</p>
          <p className={`stock ${cls}`}><span className="dot" />{label} ({p.available} available)</p>
          <div className="row">
            <input className="qtyin" type="number" min="1" max={Math.max(1, p.available)} value={qty} onChange={(e) => setQty(Math.max(1, Number(e.target.value)))} aria-label="Quantity" />
            <button className="add inline" disabled={p.available === 0} onClick={() => addToCart(p, qty)}><CartIcon /> Add to Cart</button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ----------------------------------- Cart --------------------------------- */
function Cart({ cart, setCart, startPay, notify, goShop }) {
  const key = useRef(crypto.randomUUID()); // same key if the button is clicked twice => one order
  const [busy, setBusy] = useState(false);
  async function setQty(pid, qty) {
    try { setCart(await api("/cart/items", { method: "PUT", body: { product_id: pid, qty } })); } catch (e) { notify(e.message, true); }
  }
  async function checkout() {
    if (busy) return;
    setBusy(true);
    try {
      const o = await api("/checkout", { method: "POST", headers: { "Idempotency-Key": key.current } });
      key.current = crypto.randomUUID();
      setCart({ items: [], total: 0 }); startPay(o);
    } catch (e) { notify(e.message, true); setCart(await api("/cart")); }
    setBusy(false);
  }
  if (!cart.items.length) return <div className="panel"><p className="muted">Your cart is empty.</p><button className="add inline" onClick={goShop}>Browse products</button></div>;
  return (
    <div className="panel">
      <h1>Your cart</h1>
      {cart.items.map((i) => (
        <div className="line" key={i.id}>
          <Pic p={i.product} className="mini" />
          <span className="grow">{i.product.name}<small>{money(i.product.price)} each</small></span>
          <span className="qty">
            <button onClick={() => setQty(i.product_id, i.qty - 1)} aria-label="Decrease quantity">−</button>{i.qty}
            <button onClick={() => setQty(i.product_id, i.qty + 1)} aria-label="Increase quantity">+</button>
          </span>
          <b>{money(i.product.price * i.qty)}</b>
          <button className="link danger" onClick={() => setQty(i.product_id, 0)}>Remove</button>
        </div>
      ))}
      <div className="total"><span>Total</span><b>{money(cart.total)}</b></div>
      <p className="muted">Checking out holds your items for 5 minutes while you pay.</p>
      <button className="add wide" disabled={busy} onClick={checkout}>Reserve items and continue to payment</button>
    </div>
  );
}

/* ---------------------------------- Payment -------------------------------- */
function Pay({ order, setOrder, notify, goOrders, goShop }) {
  const [left, setLeft] = useState(order.seconds_left);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (order.status !== "RESERVED") return;
    const t = setInterval(() => setLeft((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(t);
  }, [order.status]);
  useEffect(() => { // when the timer reaches 0, ask the server what happened
    if (order.status === "RESERVED" && left === 0) api(`/orders/${order.id}`).then(setOrder).catch(() => {});
  }, [left]);

  async function submit(path, body) {
    if (busy) return;
    setBusy(true);
    try { // one idempotency key per order => a double click can never charge twice
      setOrder(await api(path, { method: "POST", body, headers: { "Idempotency-Key": `pay-${order.id}` } }));
    } catch (e) { notify(e.message, true); setOrder(await api(`/orders/${order.id}`)); }
    setBusy(false);
  }
  const mm = String(Math.floor(left / 60)).padStart(2, "0"), ss = String(left % 60).padStart(2, "0");
  const message = { PAID: "Payment received. Thank you!", FAILED: "The payment failed. Your items were released.",
    EXPIRED: "The payment timed out or the hold expired. Your items were released.", CANCELLED: "Order cancelled." }[order.status];
  return (
    <div className="panel narrow">
      <h1>Order #{order.id}</h1>
      <p><span className={`status s-${order.status}`}>{order.status}</span></p>
      {order.items.map((i) => <div className="line" key={i.product_id}><span className="grow">{i.qty} × {i.name}</span><span>{money(i.qty * i.unit_price)}</span></div>)}
      <div className="total"><span>Total</span><b>{money(order.total)}</b></div>
      {order.status === "RESERVED" ? (
        <>
          <p className="clock" aria-live="polite">{mm}:{ss}</p>
          <p className="muted">Your items are held until the timer ends. This is a mock gateway, so choose the result to simulate:</p>
          <div className="row">
            <button className="add inline" disabled={busy} onClick={() => submit(`/orders/${order.id}/pay`, { outcome: "success" })}>Pay successfully</button>
            <button className="ghost" disabled={busy} onClick={() => submit(`/orders/${order.id}/pay`, { outcome: "failure" })}>Simulate failure</button>
            <button className="ghost" disabled={busy} onClick={() => submit(`/orders/${order.id}/pay`, { outcome: "timeout" })}>Simulate timeout</button>
          </div>
          <button className="link danger" disabled={busy} onClick={() => submit(`/orders/${order.id}/cancel`)}>Cancel this order</button>
        </>
      ) : (
        <>
          <p>{message}</p>
          <div className="row"><button className="add inline" onClick={goOrders}>View my orders</button><button className="ghost" onClick={goShop}>Keep shopping</button></div>
        </>
      )}
    </div>
  );
}

/* -------------------------------- Order history --------------------------- */
function Orders({ notify, resume }) {
  const [orders, setOrders] = useState(null);
  const load = useCallback(() => api(`/orders?user_id=${encodeURIComponent(userId)}`).then(setOrders).catch((e) => notify(e.message, true)), []);
  useEffect(() => { load(); const t = setInterval(load, 5000); return () => clearInterval(t); }, [load]);
  async function act(id, path, msg) {
    try { await api(`/orders/${id}/${path}`, { method: "POST" }); notify(msg); load(); } catch (e) { notify(e.message, true); }
  }
  if (!orders) return <p className="muted">Loading...</p>;
  if (!orders.length) return <div className="panel"><p className="muted">You have no orders yet.</p></div>;
  return (
    <div className="panel">
      <h1>My orders</h1>
      {orders.map((o) => (
        <article className="order" key={o.id}>
          <header>
            <b>Order #{o.id}</b><span className={`status s-${o.status}`}>{o.status}</span>
            <span className="muted">{new Date(o.created_at + "Z").toLocaleString()}</span><b className="grow right">{money(o.total)}</b>
          </header>
          <p>{o.items.map((i) => `${i.qty} × ${i.name}`).join(", ")}</p>
          {o.payments.map((p) => <small key={p.id} className="muted">Payment attempt: {p.outcome} ({money(p.amount)}). </small>)}
          {o.refund && <p className="refund">Refunded {money(o.refund.amount)} (simulated), {o.refund.status.toLowerCase()}.</p>}
          <div className="row">
            {o.status === "RESERVED" && <button className="add inline" onClick={() => resume(o)}>Pay now ({Math.floor(o.seconds_left / 60)}m {o.seconds_left % 60}s left)</button>}
            {o.status === "RESERVED" && <button className="ghost" onClick={() => act(o.id, "cancel", "Order cancelled, items released")}>Cancel</button>}
            {o.status === "PAID" && <button className="ghost" onClick={() => act(o.id, "refund", "Order cancelled and refunded")}>Cancel and refund</button>}
          </div>
        </article>
      ))}
    </div>
  );
}

/* ------------------------------------ App --------------------------------- */
export default function App() {
  const [view, setView] = useState({ name: "shop" });
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [cart, setCart] = useState({ items: [], total: 0 });
  const [order, setOrder] = useState(null);
  const [toast, setToast] = useState(null);
  const notify = (msg, err = false) => { setToast({ msg, err }); setTimeout(() => setToast(null), 4000); };
  useEffect(() => { api("/cart").then(setCart).catch(() => {}); }, []);

  const count = cart.items.reduce((n, i) => n + i.qty, 0);
  const go = (name, id) => { setView({ name, id }); window.scrollTo(0, 0); };
  const update = (patch) => setFilters((f) => ({ ...f, ...patch, page: patch.page ?? 1 }));
  const startPay = (o) => { setOrder(o); go("pay"); };
  async function addToCart(p, qty = 1) {
    const have = cart.items.find((i) => i.product_id === p.id)?.qty || 0;
    try {
      setCart(await api("/cart/items", { method: "PUT", body: { product_id: p.id, qty: have + qty } }));
      notify(`${qty} × ${p.name} added to your cart`);
    } catch (e) { notify(e.message, true); }
  }

  return (
    <div className="app">
      <header className="top">
        <button className="brand" onClick={() => go("shop")}>
          <Logo /><span><b>StudyHub</b><small>Smart Supplies. Brighter Future.</small></span>
        </button>
        <nav aria-label="Main">
          <button className={view.name === "shop" ? "on" : ""} onClick={() => go("shop")}>Home</button>
          <button className={view.name === "product" ? "on" : ""} onClick={() => go("shop")}>Products</button>
          <button className={view.name === "orders" ? "on" : ""} onClick={() => go("orders")}>My Orders</button>
        </nav>
        <label className="field icon topsearch">
          <SearchIcon />
          <input type="search" placeholder="Search school accessories..." value={filters.search}
            onChange={(e) => { update({ search: e.target.value }); if (view.name !== "shop") go("shop"); }} />
        </label>
        <button className="cart-icon" onClick={() => go("cart")} aria-label={`Cart, ${count} items`}><CartIcon size={26} />{count > 0 && <span className="badge">{count}</span>}</button>
        <button className="cartbtn" onClick={() => go("cart")}><CartIcon /> Cart ({count})</button>
      </header>
      <main>
        {view.name === "shop" && <Shop f={filters} update={update} open={(id) => go("product", id)} addToCart={addToCart} cart={cart} />}
        {view.name === "product" && <Product id={view.id} back={() => go("shop")} addToCart={addToCart} notify={notify} />}
        {view.name === "cart" && <Cart cart={cart} setCart={setCart} startPay={startPay} notify={notify} goShop={() => go("shop")} />}
        {view.name === "pay" && order && <Pay order={order} setOrder={setOrder} notify={notify} goOrders={() => go("orders")} goShop={() => go("shop")} />}
        {view.name === "orders" && <Orders notify={notify} resume={startPay} />}
      </main>
      {toast && <div className={`toast ${toast.err ? "bad" : ""}`} role="status">{toast.msg}</div>}
    </div>
  );
}
