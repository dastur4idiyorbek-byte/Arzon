/* ARZON Mini App — bitta umumiy katalog (rule 1).
 *
 * Har bir backend so'roviga initData yuboriladi (rule 8, 1-bosqich; phase 7.6).
 * Mahfiy kod faqat KIRITILADI (rule 4) — bu yerda kod yaratish yo'q.
 *
 * Yangilanish (MiniApp_Yangilanish_Prompt):
 *   task_2 — yangi mahsulot kartasi (do'kon yorlig'i, chegirma, Tugadi holati,
 *            "Savatga" + "Sotib olish" tugmalari);
 *   task_3 — batafsil sahifa (rasm slayderi, o'lcham/rang tanlash);
 *   task_4 — Buy Now oqimi (promo → yetkazish → tasdiqlash);
 *   task_5 — qidiruv, narx bo'yicha saralash, savat belgisi.
 */
const tg = window.Telegram ? window.Telegram.WebApp : null;
if (tg) { tg.ready(); tg.expand(); }

// config.js ARZON_API_URL ni belgilaydi. Bo'sh "" = same-origin (nisbiy so'rov).
const API = (
  typeof window.ARZON_API_URL === "string"
    ? window.ARZON_API_URL
    : "http://localhost:8000"
).replace(/\/$/, "");
const INIT_DATA = tg ? tg.initData : "";

const cart = {}; // { key: {product, soni, olcham, rang} } — key = id|olcham|rang
let allProducts = [];      // katalog keshi (qidiruv/saralash uchun)
let sortMode = "";         // "" | "asc" | "desc"
let currentProduct = null; // batafsil sahifadagi mahsulot
let selOlcham = null;      // batafsil sahifada tanlangan o'lcham
let selRang = null;        // tanlangan rang
let buyNow = null;         // Buy Now holati: {product, olcham, rang, promo, ...}
const DELIVERY_FEE = 100;  // Yetkazish narxi (som) — backend bilan mos (hozircha 100)
let cartLocation = null;   // Savat checkout uchun yuborilgan joylashuv {lat, lng}

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

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

/* Variantlar: olcham/rang maydonlari vergul bilan ro'yxat ("40, 41, 42"). */
function variantsOf(p) {
  const parse = (s) => (s || "").split(",").map((x) => x.trim()).filter(Boolean);
  return { olchamlar: parse(p.olcham), ranglar: parse(p.rang) };
}
function hasVariants(p) {
  const v = variantsOf(p);
  return v.olchamlar.length > 0 || v.ranglar.length > 0;
}

function effPrice(p) {
  return p.sotuv_narxi != null ? p.sotuv_narxi : p.narxi;
}

function priceHtml(p) {
  const sotuv = effPrice(p);
  return sotuv < p.narxi
    ? `<s class="old-price">${money(p.narxi)}</s> <b>${money(sotuv)}</b> som`
    : `<b>${money(p.narxi)}</b> som`;
}

const savedManzil = () => localStorage.getItem("arzon_manzil") || "";

/* ---------- ACOM coin balansi (header) ---------- */
let currentBalance = 0;

async function loadBalance() {
  const { ok, data } = await api("/api/balance");
  const chip = document.getElementById("balance-chip");
  if (!ok || !data) { chip.hidden = true; return; }
  currentBalance = data.coin_balans || 0;
  document.getElementById("balance-val").textContent = money(currentBalance);
  chip.hidden = false;
}

/* ---------- Balans to'ldirish oynasi (task_3) ---------- */
let topupMethods = [];
let topupSelected = null;

async function apiUpload(path, formData) {
  const res = await fetch(API + path, {
    method: "POST",
    headers: { "X-Telegram-Init-Data": INIT_DATA }, // Content-Type'ni brauzer qo'yadi
    body: formData,
  });
  let data = null;
  try { data = await res.json(); } catch (_) {}
  return { ok: res.ok, status: res.status, data };
}

function usulDetailHtml(u, summa) {
  const q = esc(u.qiymat || ""), nomi = esc(u.nomi || ""),
        egasi = esc(u.egasi || ""), izoh = esc(u.izoh || "");
  const s = `<b>${money(summa)} som</b>`;
  if (u.turi === "karta")
    return `💳 <b>${q}</b> — ${egasi} nomiga ${s} o'tkazing.`;
  if (u.turi === "telefon")
    return `📱 <b>${q}</b> raqamiga ${nomi} orqali ${s} o'tkazing.`;
  if (u.turi === "qr_kod")
    return `${u.qr_rasm_url ? `<img src="${esc(u.qr_rasm_url)}" class="qr-img">` : ""}
      🔳 Yuqoridagi QR kodni (${nomi}) skanerlab, ${s} o'tkazing.`;
  if (u.turi === "crypto")
    return `₿ <b>${q}</b> manziliga ${s}ga teng miqdorda o'tkazing.${izoh ? `<br>⚠️ ${izoh}` : ""}`;
  return `${s} o'tkazing.`;
}

async function openTopupModal(farq) {
  document.getElementById("topup-modal").hidden = false;
  const needed = money(Math.max(0, farq));
  document.getElementById("topup-msg").innerHTML =
    `Balansingiz yetarli emas.<br>Joriy: <b>${money(currentBalance)} som</b>. ` +
    `Yetishmayapti: <b>${needed} som</b>.`;
  const amt = document.getElementById("topup-amount");
  amt.value = Math.max(1, Math.ceil(farq)); // farq oldindan to'ldiriladi
  topupSelected = null;
  document.getElementById("topup-detail").hidden = true;

  const box = document.getElementById("topup-methods");
  box.innerHTML = "Yuklanmoqda...";
  const { ok, data } = await api("/api/tolov-usullari");
  topupMethods = ok && Array.isArray(data) ? data : [];
  box.innerHTML = "";
  if (topupMethods.length === 0) {
    box.innerHTML = `<p class="empty">To'lov usullari hali sozlanmagan.</p>`;
  }
  const emoji = { karta: "💳", telefon: "📱", qr_kod: "🔳", crypto: "₿" };
  topupMethods.forEach((u) => {
    const b = document.createElement("button");
    b.className = "method-btn";
    b.innerHTML = `${emoji[u.turi] || "💰"} ${esc(u.nomi)}`;
    b.onclick = () => selectMethod(u, b);
    box.appendChild(b);
  });
  // Bitta usul bo'lsa — avtomatik tanlanadi.
  if (topupMethods.length === 1) selectMethod(topupMethods[0], box.firstChild);
}

function selectMethod(u, btn) {
  topupSelected = u;
  document.querySelectorAll("#topup-methods .method-btn").forEach((x) =>
    x.classList.remove("active"));
  if (btn) btn.classList.add("active");
  const d = document.getElementById("topup-detail");
  d.innerHTML = usulDetailHtml(u, Number(document.getElementById("topup-amount").value) || 0);
  d.hidden = false;
}

function closeTopupModal() {
  document.getElementById("topup-modal").hidden = true;
  document.getElementById("topup-file").value = "";
}

document.getElementById("topup-close").onclick = closeTopupModal;
document.getElementById("topup-amount").addEventListener("input", () => {
  if (topupSelected) selectMethod(topupSelected,
    document.querySelector("#topup-methods .method-btn.active"));
});

document.getElementById("topup-submit").onclick = async () => {
  const summa = Number(document.getElementById("topup-amount").value);
  if (!summa || summa <= 0) { notify("Summani kiriting."); return; }
  const file = document.getElementById("topup-file").files[0];
  if (!file) { notify("To'lov chekini (rasm) yuklang."); return; }
  const fd = new FormData();
  fd.append("summa", summa);
  if (topupSelected) fd.append("tolov_usuli_id", topupSelected.id);
  fd.append("chek", file);
  const btn = document.getElementById("topup-submit");
  btn.disabled = true; btn.textContent = "Yuborilmoqda...";
  const { ok, data } = await apiUpload("/api/topup-request", fd);
  btn.disabled = false; btn.textContent = "Yuborish";
  if (ok) {
    closeTopupModal();
    notify("✅ So'rovingiz yuborildi! Super-admin chekni tekshirib tasdiqlaydi. " +
      "Tasdiqlangach balansingiz to'ladi.");
  } else {
    notify((data && data.detail) || "Yuborishда xatolik.");
  }
};

/* ---------- Katalog (rule 1: bitta ro'yxat, do'kon tanlash yo'q) ---------- */
async function loadCatalog() {
  const { ok, data } = await api("/api/products");
  allProducts = ok && Array.isArray(data) ? data : [];
  renderCatalog();
}

function renderCatalog() {
  const box = document.getElementById("catalog");
  const empty = document.getElementById("catalog-empty");
  const q = document.getElementById("search").value.trim().toLowerCase();

  // task_5: nom bo'yicha real vaqt filtri + narx bo'yicha saralash.
  let list = allProducts.filter((p) => !q || p.nomi.toLowerCase().includes(q));
  if (sortMode === "asc") list = [...list].sort((a, b) => effPrice(a) - effPrice(b));
  if (sortMode === "desc") list = [...list].sort((a, b) => effPrice(b) - effPrice(a));

  box.innerHTML = "";
  empty.hidden = list.length > 0;
  if (list.length === 0) {
    empty.textContent = allProducts.length === 0
      ? "Hozircha mahsulot yo'q."
      : "Qidiruv bo'yicha hech narsa topilmadi.";
    return;
  }

  list.forEach((p) => {
    const card = document.createElement("div");
    card.className = "card" + (p.tugadi ? " sold-out" : "");
    const imgSrc = p.rasm_url || (p.rasm_urls && p.rasm_urls[0]);
    const ratio = (p.rasm_nisbati || "1:1").replace(":", " / ");
    const img = imgSrc
      ? `<img src="${esc(imgSrc)}" alt="" loading="lazy">`
      : `<div class="no-img">🛍️</div>`;
    let badges = "";
    if (p.korinish === "mahfiy") badges += `<span class="card-badge">🔒</span>`;
    if (p.skidka_foizi > 0) badges += `<span class="card-badge sale">-${p.skidka_foizi}%</span>`;
    // Qisqartirilgan tavsif (task_2).
    const tavsif = (p.tavsif || "").trim();
    const qisqa = tavsif.length > 60 ? tavsif.slice(0, 57) + "..." : tavsif;

    card.innerHTML = `
      <div class="card-img" style="aspect-ratio:${ratio}">
        ${img}
        ${p.store_nomi ? `<span class="store-chip">🏪 ${esc(p.store_nomi)}</span>` : ""}
        <span class="badges">${badges}</span>
        ${p.tugadi ? `<div class="out-overlay">Tugadi</div>` : ""}
      </div>
      <div class="card-body">
        <div class="card-name">${esc(p.nomi)}</div>
        ${qisqa ? `<div class="card-desc">${esc(qisqa)}</div>` : ""}
        <div class="card-price">${priceHtml(p)}</div>
      </div>
      <div class="card-actions">
        <button class="act-cart" ${p.tugadi ? "disabled" : ""}>🛒 Savatga</button>
        <button class="act-buy" ${p.tugadi ? "disabled" : ""}>⚡ Sotib olish</button>
      </div>`;

    // Rasm/nomga bosilganda — batafsil sahifa (task_3).
    card.querySelector(".card-img").onclick = () => openDetail(p);
    card.querySelector(".card-name").onclick = () => openDetail(p);
    if (!p.tugadi) {
      card.querySelector(".act-cart").onclick = () =>
        hasVariants(p) ? openDetail(p, true) : addToCart(p, null, null);
      card.querySelector(".act-buy").onclick = () =>
        hasVariants(p) ? openDetail(p, true) : startBuyNow(p, null, null);
    }
    box.appendChild(card);
  });
}

document.getElementById("search").addEventListener("input", renderCatalog);
document.getElementById("sort").addEventListener("change", (e) => {
  sortMode = e.target.value;
  renderCatalog();
});

/* ---------- Mahsulot batafsil sahifasi (task_3) ---------- */
function openDetail(p, needVariant = false) {
  currentProduct = p;
  const v = variantsOf(p);
  // Bitta variantli guruh — avtomatik tanlanadi.
  selOlcham = v.olchamlar.length === 1 ? v.olchamlar[0] : null;
  selRang = v.ranglar.length === 1 ? v.ranglar[0] : null;

  const box = document.getElementById("product-detail");
  const imgs = (p.rasm_urls && p.rasm_urls.length ? p.rasm_urls
    : (p.rasm_url ? [p.rasm_url] : []));
  const ratio = (p.rasm_nisbati || "1:1").replace(":", " / ");

  const carousel = imgs.length
    ? `<div class="carousel-wrap">
         <div class="carousel" id="carousel" style="aspect-ratio:${ratio}">
           ${imgs.map((u) => `<img src="${esc(u)}" alt="">`).join("")}
         </div>
         ${imgs.length > 1 ? `<div class="car-counter" id="car-counter">1 / ${imgs.length}</div>` : ""}
       </div>`
    : `<div class="no-img big" style="aspect-ratio:${ratio}">🛍️</div>`;

  const chips = (values, group) => values.map((val) =>
    `<button class="chip" data-g="${group}" data-v="${esc(val)}">${esc(val)}</button>`
  ).join("");

  let variantHtml = "";
  if (v.olchamlar.length)
    variantHtml += `<div class="var-group"><div class="var-label">O'lcham:</div>
      <div class="chips">${chips(v.olchamlar, "o")}</div></div>`;
  if (v.ranglar.length)
    variantHtml += `<div class="var-group"><div class="var-label">Rang:</div>
      <div class="chips">${chips(v.ranglar, "r")}</div></div>`;

  let badges = "";
  if (p.skidka_foizi > 0) badges += `<span class="card-badge sale">-${p.skidka_foizi}%</span>`;
  if (p.tugadi) badges += `<span class="card-badge out">Tugadi</span>`;

  box.innerHTML = `
    ${carousel}
    <div class="detail-body">
      ${p.store_nomi ? `<div class="card-store">🏪 ${esc(p.store_nomi)}</div>` : ""}
      <h2 class="detail-name">${esc(p.nomi)} ${badges}</h2>
      <div class="detail-price">${priceHtml(p)}</div>
      ${variantHtml}
      ${p.tavsif ? `<p class="detail-desc">${esc(p.tavsif)}</p>` : ""}
      <div class="detail-actions">
        <button id="d-cart" class="ghost" ${p.tugadi ? "disabled" : ""}>🛒 Savatga qo'shish</button>
        <button id="d-buy" class="primary" ${p.tugadi ? "disabled" : ""}>⚡ Sotib olish</button>
      </div>
    </div>`;

  // Chip tanlash.
  box.querySelectorAll(".chip").forEach((c) => {
    const g = c.dataset.g, val = c.dataset.v;
    if ((g === "o" && val === selOlcham) || (g === "r" && val === selRang))
      c.classList.add("active");
    c.onclick = () => {
      box.querySelectorAll(`.chip[data-g="${g}"]`).forEach((x) => x.classList.remove("active"));
      c.classList.add("active");
      if (g === "o") selOlcham = val; else selRang = val;
    };
  });

  // Slayder hisoblagichi (1 / N).
  const car = box.querySelector("#carousel");
  const counter = box.querySelector("#car-counter");
  if (car && counter) {
    car.addEventListener("scroll", () => {
      const i = Math.round(car.scrollLeft / car.clientWidth) + 1;
      counter.textContent = `${Math.min(i, imgs.length)} / ${imgs.length}`;
    }, { passive: true });
  }

  const checkVariant = () => {
    const needO = v.olchamlar.length > 0 && !selOlcham;
    const needR = v.ranglar.length > 0 && !selRang;
    if (needO || needR) {
      notify("Iltimos, o'lcham va rangni tanlang.");
      return false;
    }
    return true;
  };
  if (!p.tugadi) {
    box.querySelector("#d-cart").onclick = () => {
      if (checkVariant()) addToCart(p, selOlcham, selRang);
    };
    box.querySelector("#d-buy").onclick = () => {
      if (checkVariant()) startBuyNow(p, selOlcham, selRang);
    };
  }

  switchView("product");
  if (needVariant && hasVariants(p)) notify("Avval o'lcham/rangni tanlang.");
}

document.getElementById("btn-back-detail").onclick = () => switchView("katalog");

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
function cartKey(p, olcham, rang) {
  return `${p.id}|${olcham || ""}|${rang || ""}`;
}

function addToCart(p, olcham, rang) {
  const key = cartKey(p, olcham, rang);
  if (!cart[key]) cart[key] = { product: p, soni: 0, olcham, rang };
  cart[key].soni += 1;
  renderCart();
  const variant = [olcham, rang].filter(Boolean).join(", ");
  notify(`"${p.nomi}"${variant ? ` (${variant})` : ""} savatga qo'shildi`);
}

function renderCart() {
  const box = document.getElementById("cart-items");
  const empty = document.getElementById("cart-empty");
  const summary = document.getElementById("cart-summary");
  const keys = Object.keys(cart);
  box.innerHTML = "";
  let count = 0, total = 0;
  keys.forEach((key) => {
    const { product, soni, olcham, rang } = cart[key];
    const birNarx = effPrice(product);
    count += soni;
    total += birNarx * soni;
    const variant = [olcham, rang].filter(Boolean).join(" · ");
    const row = document.createElement("div");
    row.className = "cart-row";
    row.innerHTML = `
      <div class="grow">
        <div>${esc(product.nomi)}${variant ? ` <span class="variant">(${esc(variant)})</span>` : ""}</div>
        <div class="card-store">${esc(product.store_nomi || "")} · ${money(birNarx)} som</div>
      </div>
      <div class="qty">
        <button data-a="minus">−</button><span>${soni}</span><button data-a="plus">+</button>
      </div>`;
    row.querySelector('[data-a="minus"]').onclick = () => { changeQty(key, -1); };
    row.querySelector('[data-a="plus"]').onclick = () => { changeQty(key, 1); };
    box.appendChild(row);
  });
  empty.hidden = keys.length > 0;
  summary.hidden = keys.length === 0;
  cartSubtotal = total;
  updateCartSummary();
  // task_5: savat belgisi — real vaqtda son.
  const badge = document.getElementById("cart-badge");
  badge.textContent = count;
  badge.hidden = count === 0;
  // Saqlangan manzilni taklif qilamiz.
  const manzilInput = document.getElementById("manzil");
  if (!manzilInput.value) manzilInput.value = savedManzil();
}

let cartSubtotal = 0;

function currentDeliveryFee() {
  // Yetkazish narxi faqat kuryerда (punktdan olish bepul).
  return deliveryType === "kuryer" && cartSubtotal > 0 ? DELIVERY_FEE : 0;
}

function updateCartSummary() {
  const fee = currentDeliveryFee();
  const sub = document.getElementById("cart-subtotal");
  const feeRow = document.getElementById("deliv-fee-row");
  const feeEl = document.getElementById("cart-fee");
  if (sub) sub.textContent = money(cartSubtotal) + " som";
  if (feeEl) feeEl.textContent = money(fee) + " som";
  if (feeRow) feeRow.style.display = fee > 0 ? "flex" : "none";
  document.getElementById("cart-total").textContent = money(cartSubtotal + fee);
}

function changeQty(key, d) {
  if (!cart[key]) return;
  cart[key].soni += d;
  if (cart[key].soni <= 0) delete cart[key];
  renderCart();
}

/* ---------- Yetkazib berish (kuryer / punkt) — savat checkout ---------- */
let deliveryType = "kuryer";
let pickupData = {}; // { store_id: [pickup points] }
let pickupChoice = {}; // { store_id: pickup_point_id }

document.getElementById("deliv-kuryer").onclick = () => setDelivery("kuryer");
document.getElementById("deliv-pickup").onclick = () => setDelivery("pickup");

function setDelivery(type) {
  deliveryType = type;
  document.getElementById("deliv-kuryer").classList.toggle("active", type === "kuryer");
  document.getElementById("deliv-pickup").classList.toggle("active", type === "pickup");
  document.getElementById("manzil").style.display = type === "kuryer" ? "block" : "none";
  const pc = document.getElementById("pickup-container");
  pc.style.display = type === "pickup" ? "block" : "none";
  if (type === "pickup") loadPickupPoints();
  updateCartSummary(); // yetkazish narxi turга qarab o'zgaradi
}

/* ---------- Joylashuv (lokatsiya) yuborish ----------
 * Telegram ilovasi ichida navigator.geolocation ko'pincha bloklanadi, shuning
 * uchun avval Telegram'ning LocationManager API'sini (8.0+) ishlatamiz,
 * bo'lmasa brauzer geolocation'ига tushamiz. */
function _okLoc(pos) {
  return pos && isFinite(pos.lat) && isFinite(pos.lng);
}

function browserGeo(finish) {
  if (!navigator.geolocation) { finish(null); return; }
  navigator.geolocation.getCurrentPosition(
    (p) => finish({ lat: +p.coords.latitude.toFixed(7), lng: +p.coords.longitude.toFixed(7) }),
    () => finish(null),
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
  );
}

/* Koordinatani qisqa manzil nomiga aylantiradi (backend orqali). */
async function reverseGeocode(loc) {
  try {
    const { ok, data } = await api(`/api/reverse-geocode?lat=${loc.lat}&lng=${loc.lng}`);
    return ok && data && data.nomi ? data.nomi : "";
  } catch (_) { return ""; }
}

function captureLocation(onOk) {
  const finish = (loc) => {
    if (_okLoc(loc)) { onOk(loc); return; }
    notify("Joylashuv olinmadi. Telegram'да ruxsat bering yoki manzilni qo'lда yozing.");
    onOk(null);
  };
  const lm = tg && tg.LocationManager;
  const has8 = tg && tg.isVersionAtLeast && tg.isVersionAtLeast("8.0");
  if (lm && has8) {
    const doGet = () => {
      if (!lm.isLocationAvailable) { browserGeo(finish); return; }
      lm.getLocation((data) => {
        if (data && data.latitude != null) {
          finish({ lat: +data.latitude.toFixed(7), lng: +data.longitude.toFixed(7) });
        } else {
          // Ruxsat berilmagan — sozlamalarni ochishni taklif qilamiz.
          notify("Joylashuvга ruxsat berilmagan. Telegram sozlamalaridан ruxsat bering.");
          if (lm.openSettings) lm.openSettings();
        }
      });
    };
    if (lm.isInited) doGet(); else lm.init(doGet);
    return;
  }
  browserGeo(finish);
}

document.getElementById("btn-location").onclick = () => {
  const btn = document.getElementById("btn-location");
  const oldTxt = btn.textContent;
  btn.textContent = "⏳ So'ralmoqda...";
  btn.disabled = true;
  captureLocation(async (loc) => {
    btn.disabled = false;
    if (!loc) { btn.textContent = oldTxt; return; }
    cartLocation = loc;
    const el = document.getElementById("loc-status");
    el.hidden = false;
    el.textContent = "⏳ Manzil aniqlanmoqda...";
    btn.textContent = "📍 Joylashuvni qayta yuborish";
    // Qisqa manzil nomini olib, maydonni avtomatik to'ldiramiz.
    const nomi = await reverseGeocode(loc);
    const manzilInput = document.getElementById("manzil");
    if (nomi) {
      manzilInput.value = nomi;
      el.textContent = "✅ Manzil: " + nomi;
    } else {
      el.textContent = "✅ Joylashuv qo'shildi";
    }
  });
  // Agar callback umumaн chaqirilmasa ham tugmani tiklaymiz.
  setTimeout(() => { if (btn.disabled) { btn.textContent = oldTxt; btn.disabled = false; } }, 15000);
};

async function fetchPickupPoints(storeIds) {
  const { ok, data } = await api("/api/pickup-points?store_ids=" + storeIds.join(","));
  const grouped = {};
  (ok && data ? data : []).forEach((p) => {
    (grouped[p.store_id] = grouped[p.store_id] || []).push(p);
  });
  return grouped;
}

async function loadPickupPoints() {
  const storeIds = [...new Set(Object.values(cart).map((c) => c.product.store_id))];
  if (storeIds.length === 0) return;
  pickupData = await fetchPickupPoints(storeIds);
  const pc = document.getElementById("pickup-container");
  pc.innerHTML = "";
  storeIds.forEach((sid) => {
    const storeName = (Object.values(cart).find((c) => c.product.store_id === sid) || {}).product?.store_nomi || ("Do'kon " + sid);
    const pts = pickupData[sid] || [];
    const box = document.createElement("div");
    box.className = "pickup-store";
    if (pts.length === 0) {
      box.innerHTML = `<div class="pickup-title">${esc(storeName)}</div><div class="empty">Bu do'konда punkt yo'q — kuryer tanlang.</div>`;
    } else {
      box.innerHTML = `<div class="pickup-title">${esc(storeName)}</div>`;
      pts.forEach((p) => {
        const lbl = document.createElement("label");
        lbl.className = "pickup-opt";
        lbl.innerHTML = `<input type="radio" name="pp_${sid}" value="${p.id}"> <b>${esc(p.nomi)}</b> — ${esc(p.manzil)}${p.ish_vaqti ? " (" + esc(p.ish_vaqti) + ")" : ""}`;
        lbl.querySelector("input").onchange = () => { pickupChoice[sid] = p.id; };
        box.appendChild(lbl);
      });
    }
    pc.appendChild(box);
  });
}

document.getElementById("btn-checkout").onclick = async () => {
  const items = Object.values(cart).map((c) => ({
    product_id: c.product.id,
    soni: c.soni,
    olcham: c.olcham || null,
    rang: c.rang || null,
  }));
  if (items.length === 0) return;
  const promo = document.getElementById("promo").value.trim() || null;

  const body = { items, promo_kod: promo, yetkazish_turi: deliveryType };
  if (deliveryType === "kuryer") {
    const manzil = document.getElementById("manzil").value.trim();
    if (!manzil) { notify("Iltimos, yetkazish manzilini kiriting."); return; }
    body.manzil = manzil;
  } else {
    const storeIds = [...new Set(Object.values(cart).map((c) => c.product.store_id))];
    const missing = storeIds.filter((sid) => !pickupChoice[sid]);
    if (missing.length > 0) { notify("Har bir do'kon uchun olib ketish punktini tanlang."); return; }
    body.pickup_points = {};
    storeIds.forEach((sid) => { body.pickup_points[sid] = pickupChoice[sid]; });
  }
  if (cartLocation) { body.lokatsiya_lat = cartLocation.lat; body.lokatsiya_lng = cartLocation.lng; }

  const neededTotal = Object.values(cart).reduce(
    (s, c) => s + effPrice(c.product) * c.soni, 0) + currentDeliveryFee();
  await submitCheckout(body, () => {
    Object.keys(cart).forEach((k) => delete cart[k]);
    cartLocation = null;
    document.getElementById("loc-status").hidden = true;
    renderCart();
  }, neededTotal);
};

async function submitCheckout(body, onSuccess, neededTotal) {
  if (body.yetkazish_turi === "kuryer" && body.manzil) {
    localStorage.setItem("arzon_manzil", body.manzil);
  }
  const { ok, status, data } = await api("/api/checkout", { method: "POST", body });
  if (ok) {
    // rule 10: bir nechta alohida buyurtma bo'lishi mumkin.
    const kodlar = data.buyurtmalar.map((o) => o.kod).join(", ");
    notify(`✅ ${data.buyurtmalar.length} ta buyurtma yaratildi. Kod(lar): ${kodlar}`);
    if (onSuccess) onSuccess();
    loadBalance(); // coin yechildi — balansni yangilaymiz
    loadOrders();
    switchView("buyurtmalar");
  } else if (status === 428) {
    notify("Iltimos, avval Savdo Botiда telefon raqamingizni tasdiqlang ('Kontaktni ulashish').");
  } else if (status === 402) {
    // task_3: balans yetmasa — ilova ichida to'ldirish oynasi (farq oldindan).
    await loadBalance();
    const farq = (neededTotal || 0) - currentBalance;
    openTopupModal(farq > 0 ? farq : (neededTotal || 0));
  } else {
    notify((data && data.detail) || "Buyurtma berishда xatolik.");
  }
}

/* ---------- Buy Now — to'g'ridan-to'g'ri checkout (task_4) ---------- */
function startBuyNow(p, olcham, rang) {
  buyNow = {
    product: p, olcham, rang, soni: 1,
    promo: null, deliv: "kuryer", manzil: savedManzil(), ppid: null,
  };
  renderBuyStep(1);
  switchView("buynow");
}

document.getElementById("btn-back-buynow").onclick = () => {
  if (currentProduct && buyNow && currentProduct.id === buyNow.product.id) {
    switchView("product");
  } else {
    switchView("katalog");
  }
};

function renderBuyStep(step) {
  const box = document.getElementById("buynow-box");
  const p = buyNow.product;
  const variant = [buyNow.olcham, buyNow.rang].filter(Boolean).join(" · ");
  const header = `
    <div class="bn-product">
      <div class="card-name">${esc(p.nomi)}${variant ? ` <span class="variant">(${esc(variant)})</span>` : ""}</div>
      <div class="card-price">${priceHtml(p)}</div>
    </div>`;

  if (step === 1) {
    // 1-qadam: promo kod (ixtiyoriy).
    box.innerHTML = `${header}
      <h3>1/3 — Promo kod</h3>
      <input id="bn-promo" type="text" placeholder="Promo kod (ixtiyoriy)"
             value="${esc(buyNow.promo || "")}" />
      <div class="row2">
        <button id="bn-skip" class="ghost">O'tkazib yuborish</button>
        <button id="bn-next" class="primary">Davom etish →</button>
      </div>`;
    box.querySelector("#bn-skip").onclick = () => { buyNow.promo = null; renderBuyStep(2); };
    box.querySelector("#bn-next").onclick = () => {
      buyNow.promo = box.querySelector("#bn-promo").value.trim() || null;
      renderBuyStep(2);
    };
    return;
  }

  if (step === 2) {
    // 2-qadam: yetkazib berish turi.
    box.innerHTML = `${header}
      <h3>2/3 — Yetkazib berish</h3>
      <div class="deliv-toggle">
        <button id="bn-kuryer" class="deliv-btn ${buyNow.deliv === "kuryer" ? "active" : ""}">🚗 Kuryer orqali</button>
        <button id="bn-pickup" class="deliv-btn ${buyNow.deliv === "pickup" ? "active" : ""}">🏬 Punktdan olib ketaman</button>
      </div>
      <input id="bn-manzil" type="text" placeholder="Yetkazish manzili (ko'cha, uy...)"
             value="${esc(buyNow.manzil || "")}"
             style="display:${buyNow.deliv === "kuryer" ? "block" : "none"}" />
      <div id="bn-pp" style="display:${buyNow.deliv === "pickup" ? "block" : "none"}"></div>
      <button id="bn-loc" class="loc-btn" type="button">📍 Joylashuvni yuborish</button>
      <div id="bn-loc-status" class="loc-status" ${buyNow.location ? "" : "hidden"}>✅ Joylashuv qo'shildi</div>
      <div class="row2">
        <button id="bn-back" class="ghost">← Orqaga</button>
        <button id="bn-next" class="primary">Davom etish →</button>
      </div>`;

    const setDeliv = (t) => {
      buyNow.deliv = t;
      box.querySelector("#bn-kuryer").classList.toggle("active", t === "kuryer");
      box.querySelector("#bn-pickup").classList.toggle("active", t === "pickup");
      box.querySelector("#bn-manzil").style.display = t === "kuryer" ? "block" : "none";
      box.querySelector("#bn-pp").style.display = t === "pickup" ? "block" : "none";
      if (t === "pickup") loadBuyNowPoints();
    };
    box.querySelector("#bn-kuryer").onclick = () => setDeliv("kuryer");
    box.querySelector("#bn-pickup").onclick = () => setDeliv("pickup");
    box.querySelector("#bn-loc").onclick = () => {
      const b = box.querySelector("#bn-loc");
      const old = b.textContent;
      b.textContent = "⏳ So'ralmoqda..."; b.disabled = true;
      captureLocation(async (loc) => {
        b.disabled = false;
        if (!loc) { b.textContent = old; return; }
        buyNow.location = loc;
        b.textContent = "📍 Joylashuvni qayta yuborish";
        const el = box.querySelector("#bn-loc-status");
        el.hidden = false;
        el.textContent = "⏳ Manzil aniqlanmoqda...";
        const nomi = await reverseGeocode(loc);
        const mInput = box.querySelector("#bn-manzil");
        if (nomi) {
          buyNow.manzil = nomi;
          if (mInput) mInput.value = nomi;
          el.textContent = "✅ Manzil: " + nomi;
        } else {
          el.textContent = "✅ Joylashuv qo'shildi";
        }
      });
      setTimeout(() => { if (b.disabled) { b.textContent = old; b.disabled = false; } }, 15000);
    };
    if (buyNow.deliv === "pickup") loadBuyNowPoints();

    box.querySelector("#bn-back").onclick = () => renderBuyStep(1);
    box.querySelector("#bn-next").onclick = () => {
      if (buyNow.deliv === "kuryer") {
        const m = box.querySelector("#bn-manzil").value.trim();
        if (!m) { notify("Iltimos, yetkazish manzilini kiriting."); return; }
        buyNow.manzil = m;
      } else if (!buyNow.ppid) {
        notify("Iltimos, olib ketish punktini tanlang.");
        return;
      }
      renderBuyStep(3);
    };
    return;
  }

  // 3-qadam: yakuniy tasdiqlash.
  const sotuv = effPrice(p);
  const mahsulotJami = sotuv * buyNow.soni;
  const fee = buyNow.deliv === "kuryer" ? DELIVERY_FEE : 0;
  const jami = mahsulotJami + fee;
  const yetk = buyNow.deliv === "kuryer"
    ? `🚗 Kuryer — ${esc(buyNow.manzil)}`
    : `🏬 Punktdan olib ketish — ${esc(buyNow.ppNomi || "")}`;
  box.innerHTML = `${header}
    <h3>3/3 — Tasdiqlash</h3>
    <div class="bn-summary">
      <div class="bn-row"><span>Soni:</span><b>${buyNow.soni} dona</b></div>
      ${variant ? `<div class="bn-row"><span>Variant:</span><b>${esc(variant)}</b></div>` : ""}
      <div class="bn-row"><span>Mahsulotlar:</span><b>${money(mahsulotJami)} som</b></div>
      ${p.skidka_foizi > 0 ? `<div class="bn-row"><span>Chegirma:</span><b>-${p.skidka_foizi}%</b></div>` : ""}
      ${buyNow.promo ? `<div class="bn-row"><span>Promo:</span><b>${esc(buyNow.promo)} (tekshiriladi)</b></div>` : ""}
      <div class="bn-row"><span>Yetkazish turi:</span><b>${yetk}</b></div>
      ${fee > 0 ? `<div class="bn-row"><span>🚚 Yetkazish narxi:</span><b>${money(fee)} som</b></div>` : ""}
      ${buyNow.location ? `<div class="bn-row"><span>📍 Joylashuv:</span><b>qo'shildi</b></div>` : ""}
      <div class="bn-row total"><span>Jami:</span><b>${money(jami)} som</b></div>
    </div>
    <div class="row2">
      <button id="bn-back" class="ghost">← Orqaga</button>
      <button id="bn-confirm" class="primary">✅ Buyurtmani tasdiqlash</button>
    </div>`;
  box.querySelector("#bn-back").onclick = () => renderBuyStep(2);
  box.querySelector("#bn-confirm").onclick = async () => {
    const body = {
      items: [{
        product_id: p.id, soni: buyNow.soni,
        olcham: buyNow.olcham || null, rang: buyNow.rang || null,
      }],
      promo_kod: buyNow.promo,
      yetkazish_turi: buyNow.deliv,
    };
    if (buyNow.deliv === "kuryer") body.manzil = buyNow.manzil;
    else body.pickup_points = { [p.store_id]: buyNow.ppid };
    if (buyNow.location) { body.lokatsiya_lat = buyNow.location.lat; body.lokatsiya_lng = buyNow.location.lng; }
    await submitCheckout(body, () => { buyNow = null; }, jami);
  };
}

async function loadBuyNowPoints() {
  const p = buyNow.product;
  const grouped = await fetchPickupPoints([p.store_id]);
  const pts = grouped[p.store_id] || [];
  const box = document.querySelector("#bn-pp");
  if (!box) return;
  if (pts.length === 0) {
    box.innerHTML = `<div class="empty">Bu do'konда punkt yo'q — kuryer tanlang.</div>`;
    return;
  }
  box.innerHTML = "";
  pts.forEach((pt) => {
    const lbl = document.createElement("label");
    lbl.className = "pickup-opt";
    lbl.innerHTML = `<input type="radio" name="bn_pp" value="${pt.id}" ${buyNow.ppid === pt.id ? "checked" : ""}> <b>${esc(pt.nomi)}</b> — ${esc(pt.manzil)}${pt.ish_vaqti ? " (" + esc(pt.ish_vaqti) + ")" : ""}`;
    lbl.querySelector("input").onchange = () => {
      buyNow.ppid = pt.id;
      buyNow.ppNomi = pt.nomi;
    };
    box.appendChild(lbl);
  });
}

/* ---------- Buyurtmalar ---------- */
const HOLAT_INFO = {
  yangi: { emoji: "🆕", matn: "Yangi", cls: "st-new" },
  tayyorlanmoqda: { emoji: "👨‍🍳", matn: "Tayyorlanmoqda", cls: "st-prep" },
  yolda: { emoji: "🚚", matn: "Yo'lda", cls: "st-way" },
  topshirildi: { emoji: "✅", matn: "Topshirildi", cls: "st-done" },
  bekor_qilindi: { emoji: "❌", matn: "Bekor qilindi", cls: "st-cancel" },
};

async function loadOrders() {
  const { ok, data } = await api("/api/orders");
  const box = document.getElementById("orders");
  const empty = document.getElementById("orders-empty");
  box.innerHTML = "";
  if (!ok || !data || data.length === 0) { empty.hidden = false; return; }
  empty.hidden = true;
  data.forEach((o) => {
    const st = HOLAT_INFO[o.holat] || { emoji: "•", matn: o.holat, cls: "" };
    const yetk = o.yetkazish_turi === "kuryer" ? "🚚 Kuryer" : "🏬 Punktdan olish";
    const feeRow = o.yetkazish_narxi
      ? `<div class="oc-row"><span>Yetkazish</span><span>${money(o.yetkazish_narxi)} som</span></div>` : "";
    const el = document.createElement("div");
    el.className = "order-card";
    el.innerHTML = `
      <div class="oc-head">
        <span class="oc-label">Buyurtma kodi</span>
        <span class="status-badge ${st.cls}">${st.emoji} ${st.matn}</span>
      </div>
      <div class="oc-code">${esc(o.kod)}</div>
      <div class="oc-rows">
        <div class="oc-row"><span>${yetk}</span><span></span></div>
        ${feeRow}
        <div class="oc-row oc-total"><span>Jami</span><span>${money(o.jami_narx)} som</span></div>
      </div>`;
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
      <p>Karta: <b>${esc(data.karta_turi || "yo'q")}</b></p>
      ${qolgan}
      <hr style="opacity:.2;margin:12px 0">
      <div class="card-store">Referal havolangiz (${data.taklif_qilganlar} taklif):</div>
      <div class="ref-link">${esc(data.referal_havola)}</div>
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
  window.scrollTo(0, 0);
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
loadBalance();
renderCart();
