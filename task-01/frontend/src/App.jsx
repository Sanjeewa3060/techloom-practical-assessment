import { useCallback, useEffect, useRef, useState } from "react";
import { api, userId } from "./api";

const money = (n) => `$${Number(n).toFixed(2)}`;

/* ---------- shared hook: poll a path so stock levels stay live ---------- */
function useLive(path, ms = 4000) {
  const [data, setData] = useState([]);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    try { setData(await api(path)); setError(""); } catch (e) { setError(e.message); }
  }, [path]);
  useEffect(() => { load(); const t = setInterval(load, ms); return () => clearInterval(t); }, [load, ms]);
  return [data, load, error];
}

/* ------------------------------ Inventory ------------------------------ */
function Inventory({ notify }) {
  const [products, reload] = useLive("/products");
  const empty = { name: "", price: "", stock_total: "", image_url: "" };
  const [form, setForm] = useState(empty);
  const [editId, setEditId] = useState(null);

  async function save(e) {
    e.preventDefault();
    const body = { name: form.name, price: Number(form.price), stock_total: Number(form.stock_total), image_url: form.image_url || null };
    try {
      await api(editId ? `/products/${editId}` : "/products", { method: editId ? "PUT" : "POST", body });
      notify(editId ? "Product updated" : "Product added");
      setForm(empty); setEditId(null); reload();
    } catch (err) { notify(err.message, true); }
  }
  async function remove(id) {
    try { await api(`/products/${id}`, { method: "DELETE" }); notify("Product deleted"); reload(); }
    catch (err) { notify(err.message, true); }
  }

  return (
    <section>
      <form className="row form" onSubmit={save}>
        <input placeholder="Product name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input placeholder="Price" type="number" step="0.01" min="0" required value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} />
        <input placeholder="Stock" type="number" min="0" required value={form.stock_total} onChange={(e) => setForm({ ...form, stock_total: e.target.value })} />
        <input placeholder="Image path (e.g. /images/backpack.svg)" value={form.image_url} onChange={(e) => setForm({ ...form, image_url: e.target.value })} />
        <button className="primary">{editId ? "Save changes" : "Add product"}</button>
        {editId && <button type="button" onClick={() => { setEditId(null); setForm(empty); }}>Cancel</button>}
      </form>
      <table>
        <thead><tr><th>Product</th><th>Price</th><th>On shelf</th><th>Reserved</th><th>Available</th><th /></tr></thead>
        <tbody>
          {products.map((p) => (
            <tr key={p.id}>
              <td className="namecell">{p.image_url && <img className="thumb" src={p.image_url} alt="" />}{p.name}</td><td>{money(p.price)}</td><td>{p.stock_total}</td><td>{p.stock_reserved}</td>
              <td><b className={p.available === 0 ? "out" : ""}>{p.available}</b></td>
              <td className="actions">
                <button onClick={() => { setEditId(p.id); setForm({ name: p.name, price: p.price, stock_total: p.stock_total, image_url: p.image_url || "" }); }}>Edit</button>
                <button className="danger" onClick={() => remove(p.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

/* ------------------------------- Register ------------------------------ */
function Register({ notify, goOrders }) {
  const [products, reloadProducts] = useLive("/products");
  const [cart, setCart] = useState({ items: [], total: 0 });
  const [order, setOrder] = useState(null);
  const checkoutKey = useRef(crypto.randomUUID()); // same key on double-click => one order

  const loadCart = useCallback(async () => setCart(await api("/cart")), []);
  useEffect(() => { loadCart(); }, [loadCart]);

  async function setQty(product_id, qty) {
    try { setCart(await api("/cart/items", { method: "PUT", body: { product_id, qty } })); }
    catch (e) { notify(e.message, true); }
  }
  async function checkout() {
    try {
      const o = await api("/checkout", { method: "POST", headers: { "Idempotency-Key": checkoutKey.current } });
      checkoutKey.current = crypto.randomUUID();
      setOrder(o); loadCart(); reloadProducts();
    } catch (e) { notify(e.message, true); loadCart(); reloadProducts(); }
  }
  const inCart = (id) => cart.items.find((i) => i.product_id === id)?.qty || 0;

  return (
    <div className="split">
      <section>
        <h2>Products</h2>
        <div className="grid">
          {products.map((p) => (
            <div className="tile" key={p.id}>
              {p.image_url && <img className="pic" src={p.image_url} alt={p.name} loading="lazy" />}
              <b>{p.name}</b><span>{money(p.price)}</span>
              <small className={p.available === 0 ? "out" : ""}>{p.available} available</small>
              <button disabled={p.available <= inCart(p.id)} onClick={() => setQty(p.id, inCart(p.id) + 1)}>Add</button>
            </div>
          ))}
        </div>
      </section>
      <aside>
        {order ? (
          <Payment order={order} setOrder={setOrder} notify={notify} reload={reloadProducts} goOrders={goOrders} />
        ) : (
          <>
            <h2>Cart</h2>
            {cart.items.length === 0 && <p className="muted">Nothing in the cart yet.</p>}
            {cart.items.map((i) => (
              <div className="line" key={i.id}>
                <span>{i.product.name}</span>
                <span className="qty">
                  <button onClick={() => setQty(i.product_id, i.qty - 1)}>−</button>{i.qty}
                  <button onClick={() => setQty(i.product_id, i.qty + 1)}>+</button>
                </span>
                <span>{money(i.product.price * i.qty)}</span>
              </div>
            ))}
            <div className="total"><span>Total</span><b>{money(cart.total)}</b></div>
            <button className="primary wide" disabled={!cart.items.length} onClick={checkout}>
              Reserve stock and check out
            </button>
          </>
        )}
      </aside>
    </div>
  );
}

/* ---------------- Payment panel with the 5-minute countdown -------------- */
function Payment({ order, setOrder, notify, reload, goOrders }) {
  const [left, setLeft] = useState(order.seconds_left);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (order.status !== "RESERVED") return;
    const t = setInterval(() => setLeft((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(t);
  }, [order.status]);

  async function act(path, body) {
    if (busy) return;
    setBusy(true);
    try {
      // one idempotency key per order+outcome => a double click can never charge twice
      const o = await api(path, { method: "POST", body, headers: { "Idempotency-Key": `pay-${order.id}` } });
      setOrder(o); setLeft(o.seconds_left); reload();
    } catch (e) { notify(e.message, true); setOrder(await api(`/orders/${order.id}`)); reload(); }
    setBusy(false);
  }
  const mm = String(Math.floor(left / 60)).padStart(2, "0"), ss = String(left % 60).padStart(2, "0");

  return (
    <div className="pay">
      <h2>Order #{order.id}</h2>
      <p className={`status s-${order.status}`}>{order.status}</p>
      {order.items.map((i) => <div className="line" key={i.product_id}><span>{i.qty} × {i.name}</span><span>{money(i.qty * i.unit_price)}</span></div>)}
      <div className="total"><span>Total</span><b>{money(order.total)}</b></div>
      {order.status === "RESERVED" ? (
        <>
          <div className="clock" aria-live="polite">{mm}:{ss}<small>until the reserved stock is released</small></div>
          <p className="muted">Mock gateway – choose the outcome to simulate:</p>
          <div className="row">
            <button className="primary" disabled={busy} onClick={() => act(`/orders/${order.id}/pay`, { outcome: "success" })}>Success</button>
            <button disabled={busy} onClick={() => act(`/orders/${order.id}/pay`, { outcome: "failure" })}>Failure</button>
            <button disabled={busy} onClick={() => act(`/orders/${order.id}/pay`, { outcome: "timeout" })}>Timeout</button>
          </div>
          <button className="danger wide" disabled={busy} onClick={() => act(`/orders/${order.id}/cancel`)}>Cancel order</button>
        </>
      ) : (
        <div className="row">
          <button className="primary" onClick={() => setOrder(null)}>New sale</button>
          <button onClick={goOrders}>View orders</button>
        </div>
      )}
    </div>
  );
}

/* -------------------------------- Orders ------------------------------- */
function Orders({ notify }) {
  const [orders, reload] = useLive("/orders", 3000);
  async function cancel(id) {
    try { await api(`/orders/${id}/cancel`, { method: "POST" }); notify(`Order #${id} cancelled, stock restored`); reload(); }
    catch (e) { notify(e.message, true); }
  }
  return (
    <section>
      <table>
        <thead><tr><th>Order</th><th>Customer</th><th>Items</th><th>Total</th><th>Status</th><th /></tr></thead>
        <tbody>
          {orders.map((o) => (
            <tr key={o.id}>
              <td>#{o.id}</td><td>{o.user_id}</td>
              <td>{o.items.map((i) => `${i.qty}× ${i.name}`).join(", ")}</td>
              <td>{money(o.total)}</td>
              <td><span className={`status s-${o.status}`}>{o.status}</span>{o.status === "RESERVED" && <small> {Math.floor(o.seconds_left / 60)}m {o.seconds_left % 60}s left</small>}</td>
              <td>{["RESERVED", "PAID"].includes(o.status) && <button onClick={() => cancel(o.id)}>Cancel</button>}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {orders.length === 0 && <p className="muted">No orders yet. Ring one up on the Register tab.</p>}
    </section>
  );
}

/* --------------------------------- App --------------------------------- */
export default function App() {
  const [tab, setTab] = useState("register");
  const [toast, setToast] = useState(null);
  const notify = (msg, err = false) => { setToast({ msg, err }); setTimeout(() => setToast(null), 4000); };
  return (
    <div className="app">
      <header>
        <h1>StudyHub POS</h1>
        <nav>
          {["register", "inventory", "orders"].map((t) => (
            <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>{t[0].toUpperCase() + t.slice(1)}</button>
          ))}
        </nav>
        <small className="muted">Till ID: {userId}</small>
      </header>
      <main>
        {tab === "register" && <Register notify={notify} goOrders={() => setTab("orders")} />}
        {tab === "inventory" && <Inventory notify={notify} />}
        {tab === "orders" && <Orders notify={notify} />}
      </main>
      {toast && <div className={`toast ${toast.err ? "err" : ""}`} role="status">{toast.msg}</div>}
    </div>
  );
}
