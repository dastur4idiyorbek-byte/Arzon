/* ARZON Mini App — bitta umumiy katalog (rule 1).
 *
 * Har bir backend so'roviga initData yuboriladi (rule 8, 1-bosqich; phase 7.6).
 * Mahfiy kod faqat KIRITILADI (rule 4) — bu yerda kod yaratish yo'q.
 */
const tg = window.Telegram ? window.Telegram.WebApp : null;
if (tg) { tg.ready(); tg.expand(); }

// Backend manzili — Vercel/Netlify'da build vaqtiда o'rnatiladi.
// Lokal test uchun localhost:8000.
// config.js ARZON_API_URL ni belgilaydi. Bo'sh "" = same-origin (nisbiy so'rov).
const API = (
  typeof window.ARZON_API_URL === "string"
    ? window.ARZON_API_URL
    : "http://localhost:8000"
).replace(/\/$/, "");
const INIT_DATA = tg ? tg.initData : "";

const cart = {}; // { product_id: {product, soni} }

async function api(path, { method = "GET", body } = {}) {
  const res = await fetch(API + path, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": INIT_DATA,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch (_) {}
  return { ok: res.ok, status: res.status, data };
}

function money(n) { return Number(n).toLocaleString("uz-UZ"); }

/* ---------- Katalog (rule 1: bitta ro'yxat, do'kon tanlash yo'q) ---------- */
async function loadCatalog() {
  const { ok, data } = await api("/api/products");
  const box = document.getElementById("catalog");
  const empty = document.getElementById("catalog-empty");
  box.innerHTML = "";
  if (!ok || !data || data.length === 0) {
    empty.hidden = false;
    return;
  }
  empty.hidden = true;
  data.forEach((p) => {
    const card = document.createElement("div");
    card.className = "card";
    const imgSrc = p.rasm_url || (p.rasm_urls && p.rasm_urls[0]);
    const ratio = (p.rasm_nisbati || "1:1").replace(":", " / ");
    const img = imgSrc
      ? `<img style="aspect-ratio:${ratio}" src="${imgSrc}" alt="">`
      : `<div class="no-img">🛍️</div>`;
    let badges = "";
    if (p.korinish === "mahfiy") badges += `<span class="card-badge">🔒 maxfiy</span>`;
    if (p.skidka_foizi > 0) badges += `<span class="card-badge sale">-${p.skidka_foizi}%</span>`;
    if (p.tugadi) badges += `<span class="card-badge out">Tugadi</span>`;
    // Chegirma bo'lsa: eski narx ustidan chizilgan + yangi narx.
    const sotuv = p.sotuv_narxi != null ? p.sotuv_narxi : p.narxi;
    const priceHtml =
      sotuv < p.narxi
        ? `<s class="old-price">${money(p.narxi)}</s> ${money(sotuv)} som`
        : `${money(p.narxi)} som`;
    card.innerHTML = `
      ${img}
      <div class="card-body">
        <div class="card-store">${p.store_nomi || ""}</div>
        <div class="card-name">${p.nomi}</div>
        <div>${badges}</div>
        <div class="card-price">${priceHtml}</div>
      </div>
      <button ${p.tugadi ? "disabled" : ""}>${p.tugadi ? "Tugadi" : "Savatga"}</button>`;
    const btn = card.querySelector("button");
    if (!p.tugadi) btn.onclick = () => addToCart(p);
    box.appendChild(card);
  });
}

/* ---------- Mahfiy kod kiritish (rule 3, 4) ---------- */
document.getElementById("btn-code").onclick = async () => {
  const kod = tg ? await promptCode() : prompt("Mahfiy kodni kiriting:");
  if (!kod) return;
  const { ok, data } = await api("/api/unlock", { method: "POST", body: { kod } });
  if (ok && data.ochildi) {
    notify(data.xabar || "Ochildi!");
    loadCatalog(); // yangi mahfiy mahsulotlar katalogга qo'shiladi
  } else if (data && data.status === 429) {
    notify("Juda ko'p urinish. Biroz kuting.");
  } else {
    notify((data && data.xabar) || "Kod noto'g'ri.");
  }
};

function promptCode() {
  // Telegram'да native prompt yo'q — oddiy window.prompt zaxira sifatida.
  return Promise.resolve(prompt("Do'kon mahfiy kodini kiriting:"));
}

/* ---------- Savat (rule 10: checkout'да do'kon bo'yicha ajratiladi) ---------- */
function addToCart(p) {
  if (!cart[p.id]) cart[p.id] = { product: p, soni: 0 };
  cart[p.id].soni += 1;
  renderCart();
  notify(`"${p.nomi}" savatga qo'shildi`);
}

function renderCart() {
  const box = document.getElementById("cart-items");
  const empty = document.getElementById("cart-empty");
  const summary = document.getElementById("cart-summary");
  const ids = Object.keys(cart);
  box.innerHTML = "";
  let count = 0, total = 0;
  ids.forEach((id) => {
    const { product, soni } = cart[id];
    const birNarx = product.sotuv_narxi != null ? product.sotuv_narxi : product.narxi;
    count += soni;
    total += birNarx * soni;
    const row = document.createElement("div");
    row.className = "cart-row";
    row.innerHTML = `
      <div class="grow">
        <div>${product.nomi}</div>
        <div class="card-store">${product.store_nomi || ""} · ${money(birNarx)} som</div>
      </div>
      <div class="qty">
        <button data-a="minus">−</button><span>${soni}</span><button data-a="plus">+</button>
      </div>`;
    row.querySelector('[data-a="minus"]').onclick = () => { changeQty(id, -1); };
    row.querySelector('[data-a="plus"]').onclick = () => { changeQty(id, 1); };
    box.appendChild(row);
  });
  empty.hidden = ids.length > 0;
  summary.hidden = ids.length === 0;
  document.getElementById("cart-total").textContent = money(total);
  const badge = document.getElementById("cart-badge");
  badge.textContent = count;
  badge.hidden = count === 0;
}

function changeQty(id, d) {
  if (!cart[id]) return;
  cart[id].soni += d;
  if (cart[id].soni <= 0) delete cart[id];
  renderCart();
}

document.getElementById("btn-checkout").onclick = async () => {
  const items = Object.values(cart).map((c) => ({ product_id: c.product.id, soni: c.soni }));
  if (items.length === 0) return;
  const promo = document.getElementById("promo").value.trim() || null;
  const { ok, status, data } = await api("/api/checkout", {
    method: "POST",
    body: { items, promo_kod: promo },
  });
  if (ok) {
    // rule 10: bir nechta alohida buyurtma bo'lishi mumkin.
    const kodlar = data.buyurtmalar.map((o) => o.kod).join(", ");
    notify(`✅ ${data.buyurtmalar.length} ta buyurtma yaratildi. Kod(lar): ${kodlar}`);
    Object.keys(cart).forEach((k) => delete cart[k]);
    renderCart();
    loadOrders();
    switchView("buyurtmalar");
  } else if (status === 428) {
    notify("Iltimos, avval Savdo Botiда telefon raqamingizni tasdiqlang ('Kontaktni ulashish').");
  } else {
    notify((data && data.detail) || "Buyurtma berishда xatolik.");
  }
};

/* ---------- Buyurtmalar ---------- */
async function loadOrders() {
  const { ok, data } = await api("/api/orders");
  const box = document.getElementById("orders");
  const empty = document.getElementById("orders-empty");
  box.innerHTML = "";
  if (!ok || !data || data.length === 0) { empty.hidden = false; return; }
  empty.hidden = true;
  data.forEach((o) => {
    const el = document.createElement("div");
    el.className = "order-card";
    el.innerHTML = `
      <div class="code">${o.kod}</div>
      <div>${money(o.jami_narx)} so'm</div>
      <div class="status">Holat: ${o.holat}</div>`;
    box.appendChild(el);
  });
}

/* ---------- Chat ---------- */
document.getElementById("btn-send").onclick = sendChat;
document.getElementById("chat-text").addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendChat();
});
async function sendChat() {
  const input = document.getElementById("chat-text");
  const matn = input.value.trim();
  if (!matn) return;
  input.value = "";
  addMsg(matn, "user");
  const { ok, data } = await api("/api/chat", { method: "POST", body: { matn } });
  addMsg(ok && data ? data.javob : "Xatolik yuz berdi.", "bot");
}
function addMsg(text, who) {
  const log = document.getElementById("chat-log");
  const el = document.createElement("div");
  el.className = "msg " + who;
  el.textContent = text;
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
}

/* ---------- Sodiqlik (rule 9) ---------- */
async function loadLoyalty() {
  const { ok, data } = await api("/api/loyalty");
  const box = document.getElementById("loyalty");
  if (!ok || !data) { box.innerHTML = "<p class='empty'>Ma'lumot yo'q.</p>"; return; }
  const qolgan = data.keyingi_karta_uchun_qolgan
    ? `<p>Keyingi karta uchun yana <b>${data.keyingi_karta_uchun_qolgan}</b> ta xarid.</p>` : "";
  box.innerHTML = `
    <div class="loyalty-box">
      <div class="card-store">Umumiy xaridlar</div>
      <div class="big">${data.umumiy_xaridlar}</div>
      <p>Karta: <b>${data.karta_turi || "yo'q"}</b></p>
      ${qolgan}
      <hr style="opacity:.2;margin:12px 0">
      <div class="card-store">Referal havolangiz (${data.taklif_qilganlar} taklif):</div>
      <div class="ref-link">${data.referal_havola}</div>
    </div>`;
}

/* ---------- Navigatsiya ---------- */
function switchView(name) {
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  document.getElementById("view-" + name).classList.add("active");
  document.querySelectorAll(".tab").forEach((t) =>
    t.classList.toggle("active", t.dataset.view === name)
  );
  if (name === "buyurtmalar") loadOrders();
  if (name === "sodiqlik") loadLoyalty();
}
document.querySelectorAll(".tab").forEach((t) => {
  t.onclick = () => switchView(t.dataset.view);
});

function notify(text) {
  if (tg && tg.showAlert) tg.showAlert(text);
  else alert(text);
}

/* ---------- Boshlash ---------- */
loadCatalog();
renderCart();
