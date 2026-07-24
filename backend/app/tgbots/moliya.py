"""Moliya Boti — faqat super-admin (ACOM coin so'rovlarini tasdiqlaydi).

Menyu:
    🔔 To'ldirish so'rovlari    💸 Pul yechish so'rovlari
    ↩️ Qaytarish so'rovlari      📊 Umumiy hisobot
    💳 To'lov usullari

Rule 2: yakuniy qaror HAR DOIM shu yerда super-admin tugma bosishи bilan
beriladi — AI xulosasidan qat'i nazar. Barcha summalar KGS (Qirg'iziston somi).
"""
from __future__ import annotations

import logging

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from ..config import settings
from .client import api

logger = logging.getLogger("arzon.moliya")

BTN_TOPUPS = "🔔 To'ldirish so'rovlari"
BTN_WITHDRAWS = "💸 Pul yechish so'rovlari"
BTN_REFUNDS = "↩️ Qaytarish so'rovlari"
BTN_DOKON_TOLOV = "🏪 Do'kon to'lovlari"
BTN_REPORT = "📊 Umumiy hisobot"
BTN_METHODS = "💳 To'lov usullari"
BTN_HOME = "🏠 Bosh menyu"

# Conversation holatlari.
(R_SABAB, M_TURI, M_STEP, M_QR, ME_NOMI, ME_QIYMAT) = range(6)

_TURI_EMOJI = {"karta": "💳", "telefon": "📱", "qr_kod": "🔳", "crypto": "₿"}

# Har tur uchun so'raladigan maydonlar ketma-ketligi (task_2).
_FIELD_SEQ = {
    "karta": [
        ("nomi", "Bank/usul nomini kiriting (masalan Optima Bank):"),
        ("qiymat", "Karta raqamini kiriting:"),
        ("egasi", "Karta egasining ismini kiriting:"),
    ],
    "telefon": [
        ("nomi", "Xizmat nomini kiriting (Elsom / O'Dengi / Balance.kg...):"),
        ("qiymat", "Telefon raqamini kiriting:"),
        ("egasi", "Egasining ismini kiriting:"),
    ],
    "crypto": [
        ("nomi", "Coin turini kiriting (masalan USDT):"),
        ("qiymat", "Crypto manzilini (adres) kiriting:"),
        ("izoh", "Tarmoq/izoh kiriting (masalan 'Faqat TRC20 tarmog'idan'):"),
    ],
    "qr_kod": [
        ("nomi", "Usul nomini kiriting (masalan MBANK QR):"),
    ],
}


def _is_super(uid: int) -> bool:
    return uid in settings.super_admin_id_list


def menu_markup() -> InlineKeyboardMarkup:
    # Inline menyu (Menyu_Inline_Prompt).
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(BTN_TOPUPS, callback_data="fm:topups"),
             InlineKeyboardButton(BTN_WITHDRAWS, callback_data="fm:withdraws")],
            [InlineKeyboardButton(BTN_REFUNDS, callback_data="fm:refunds"),
             InlineKeyboardButton(BTN_DOKON_TOLOV, callback_data="fm:dokon_tolov")],
            [InlineKeyboardButton(BTN_METHODS, callback_data="fm:methods"),
             InlineKeyboardButton(BTN_REPORT, callback_data="fm:report")],
        ]
    )


def back_home_f() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Bosh menyu", callback_data="fm:home")]]
    )


def cancel_kb_f() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Bekor qilish", callback_data="conv:cancel")]]
    )


async def menu_home_f(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    try:
        await q.edit_message_text("Bosh menyu 👇", reply_markup=menu_markup())
    except Exception:  # noqa: BLE001
        await update.effective_message.reply_text("Bosh menyu 👇", reply_markup=menu_markup())


async def menu_router_f(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    key = q.data.split(":", 1)[1]
    fn = {"topups": topups, "withdraws": withdraws, "refunds": refunds,
          "dokon_tolov": dokon_tolovlari, "report": report, "methods": methods}.get(key)
    if fn:
        await fn(update, context)


async def cancel_conv_f(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    context.user_data.clear()
    await update.effective_message.reply_text(
        "❌ Bekor qilindi. Bosh menyu 👇", reply_markup=menu_markup()
    )
    return ConversationHandler.END


async def _guard(update: Update) -> bool:
    if not _is_super(update.effective_user.id):
        await update.effective_message.reply_text(
            "⛔️ Bu bot faqat super-admin (loyiha egasi) uchun."
        )
        return False
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    # Eski pastki (reply) klaviaturани olib tashlaymiz — endi faqat inline menyu.
    await update.effective_message.reply_text(
        "💰 ARZON Moliya Boti", reply_markup=ReplyKeyboardRemove()
    )
    await update.effective_message.reply_text(
        "ACOM coin so'rovlarini boshqaring 👇", reply_markup=menu_markup()
    )


# ---------------------------------------------------------------------------
# To'ldirish so'rovlari
# ---------------------------------------------------------------------------
def _topup_kb(sorov_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"mt_ok_{sorov_id}"),
                InlineKeyboardButton("❌ Rad etish", callback_data=f"mt_no_{sorov_id}"),
            ]
        ]
    )


async def topups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    uid = update.effective_user.id
    rows = await api.moliya_topups(uid)
    if not rows:
        await update.effective_message.reply_text("Kutilayotgan to'ldirish so'rovi yo'q. ✅")
        return
    xulosa_map = {
        "mos_keladi": "✅ Mos keladi",
        "mos_kelmaydi": "⚠️ Mos kelmaydi",
        "aniq_emas": "❓ Aniq emas",
    }
    for s in rows[:20]:
        ai_txt = (
            f"🤖 Gemini: {s['ai_summa']:,.0f} som"
            + (f", {s['ai_sana']}" if s.get("ai_sana") else "")
            if s.get("ai_summa") is not None
            else "🤖 Gemini: o'qilmadi"
        )
        text = (
            f"🔔 So'rov #{s['id']}\n"
            f"👤 {s.get('ism') or 'nomalum'}, {s.get('telegram_id')}\n"
            f"💰 Kiritgan: {s['summa']:,.0f} som\n"
            f"{ai_txt}\n"
            f"AI xulosasi: {xulosa_map.get(s.get('ai_xulosa'), '❓')}"
        )
        base = _base_url()
        if s.get("chek_rasm_url") and base:
            try:
                await context.bot.send_photo(
                    chat_id=uid,
                    photo=f"{base}{s['chek_rasm_url']}",
                    caption=text,
                    reply_markup=_topup_kb(s["id"]),
                )
                continue
            except Exception:  # noqa: BLE001
                pass
        await update.effective_message.reply_text(text, reply_markup=_topup_kb(s["id"]))


async def topup_approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_super(update.effective_user.id):
        await query.answer("Faqat super-admin.", show_alert=True)
        return
    await query.answer()
    sorov_id = int(query.data.replace("mt_ok_", ""))
    r = await api.moliya_topup_approve(update.effective_user.id, sorov_id)
    if r.status_code == 200:
        yangi = r.json().get("yangi_balans")
        await _edit(query, f"✅ Tasdiqlandi. Mijoz balansi: {yangi:,.0f} ACOM")
    else:
        await _edit(query, f"❌ Xatolik: {r.text[:200]}")


# ---------------------------------------------------------------------------
# Pul yechish so'rovlari
# ---------------------------------------------------------------------------
async def withdraws(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    rows = await api.moliya_withdraws(update.effective_user.id)
    if not rows:
        await update.effective_message.reply_text("Kutilayotgan pul yechish so'rovi yo'q. ✅")
        return
    for s in rows[:20]:
        text = (
            f"💸 So'rov #{s['id']}\n"
            f"🏪 {s.get('store_nomi')}\n"
            f"💰 {s['summa']:,.0f} som\n"
            f"💳 {s['karta_raqami']}"
        )
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ To'landi", callback_data=f"mw_ok_{s['id']}")]]
        )
        await update.effective_message.reply_text(text, reply_markup=kb)


async def withdraw_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_super(update.effective_user.id):
        await query.answer("Faqat super-admin.", show_alert=True)
        return
    await query.answer()
    sorov_id = int(query.data.replace("mw_ok_", ""))
    r = await api.moliya_withdraw_paid(update.effective_user.id, sorov_id)
    if r.status_code == 200:
        await _edit(query, "✅ To'landi deb belgilandi.")
    else:
        await _edit(query, f"❌ Xatolik: {r.text[:200]}")


# ---------------------------------------------------------------------------
# Qaytarish so'rovlari
# ---------------------------------------------------------------------------
async def refunds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    rows = await api.moliya_refunds(update.effective_user.id)
    if not rows:
        await update.effective_message.reply_text("Kutilayotgan qaytarish so'rovi yo'q. ✅")
        return
    for s in rows[:20]:
        text = (
            f"↩️ So'rov #{s['id']}\n"
            f"👤 {s.get('ism') or 'nomalum'}, {s.get('telegram_id')}\n"
            f"💰 {s['summa']:,.0f} som\n"
            f"💳 {s['karta_raqami']}"
        )
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"mr_ok_{s['id']}"),
                    InlineKeyboardButton("❌ Rad etish", callback_data=f"mr_no_{s['id']}"),
                ]
            ]
        )
        await update.effective_message.reply_text(text, reply_markup=kb)


async def refund_approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_super(update.effective_user.id):
        await query.answer("Faqat super-admin.", show_alert=True)
        return
    await query.answer()
    sorov_id = int(query.data.replace("mr_ok_", ""))
    r = await api.moliya_refund_approve(update.effective_user.id, sorov_id)
    if r.status_code == 200:
        await _edit(query, "✅ Qaytarish tasdiqlandi.")
    else:
        await _edit(query, f"❌ Xatolik: {r.text[:200]}")


# ---------------------------------------------------------------------------
# Rad etish (sabab bilan) — to'ldirish va qaytarish uchun umumiy conversation
# ---------------------------------------------------------------------------
async def reject_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not _is_super(update.effective_user.id):
        await query.answer("Faqat super-admin.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    data = query.data
    if data.startswith("mt_no_"):
        context.user_data["reject"] = ("topup", int(data.replace("mt_no_", "")))
    elif data.startswith("dt_no_"):
        context.user_data["reject"] = ("dokon_tolov", int(data.replace("dt_no_", "")))
    else:
        context.user_data["reject"] = ("refund", int(data.replace("mr_no_", "")))
    await query.message.reply_text(
        "❌ Rad etish sababini yozing (so'rovchiga yuboriladi):",
        reply_markup=cancel_kb_f(),
    )
    return R_SABAB


async def reject_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    turi_id = context.user_data.pop("reject", None)
    if not turi_id:
        return ConversationHandler.END
    turi, sorov_id = turi_id
    sabab = update.message.text.strip()
    uid = update.effective_user.id
    if turi == "topup":
        r = await api.moliya_topup_reject(uid, sorov_id, sabab)
    elif turi == "dokon_tolov":
        r = await api.moliya_dokon_tolov_reject(uid, sorov_id, sabab)
    else:
        r = await api.moliya_refund_reject(uid, sorov_id, sabab)
    msg = "✅ Rad etildi, so'rovchiga xabar berildi." if r.status_code == 200 else f"❌ {r.text[:200]}"
    await update.effective_message.reply_text(msg, reply_markup=menu_markup())
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# 🏪 Do'kon ochish to'lovlari (hisobchi to'lovni tasdiqlaydi -> Menejerga)
# ---------------------------------------------------------------------------
async def dokon_tolovlari(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    uid = update.effective_user.id
    rows = await api.moliya_dokon_tolovlari(uid)
    if not rows:
        await update.effective_message.reply_text("Kutilayotgan do'kon to'lovi yo'q. ✅")
        return
    xmap = {"mos_keladi": "✅ Mos", "mos_kelmaydi": "⚠️ Mos emas", "aniq_emas": "❓"}
    for s in rows[:20]:
        ai = (
            f"🤖 Gemini: {s['ai_summa']:,.0f} som"
            if s.get("ai_summa") is not None
            else "🤖 Gemini: o'qilmadi"
        )
        text = (
            f"🏪 Do'kon to'lovi #{s['id']}\n"
            f"Do'kon: {s['dokon_nomi']}\n"
            f"So'rovchi: {s.get('ism') or 'nomalum'}, {s.get('telegram_id')}\n"
            f"Mahsulot soni: {s['mahsulot_soni']} ta\n"
            f"To'lov: {s['summa']:,.0f} som\n"
            f"{ai} — {xmap.get(s.get('ai_xulosa'), '❓')}"
        )
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ To'lov tasdiqlash", callback_data=f"dt_ok_{s['id']}"),
                    InlineKeyboardButton("❌ Rad etish", callback_data=f"dt_no_{s['id']}"),
                ]
            ]
        )
        base = _base_url()
        if s.get("chek_rasm_url") and base:
            try:
                await context.bot.send_photo(
                    chat_id=uid, photo=f"{base}{s['chek_rasm_url']}",
                    caption=text, reply_markup=kb,
                )
                continue
            except Exception:  # noqa: BLE001
                pass
        await update.effective_message.reply_text(text, reply_markup=kb)


async def dokon_tolov_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_super(update.effective_user.id):
        await query.answer("Faqat super-admin.", show_alert=True)
        return
    await query.answer()
    sorov_id = int(query.data.replace("dt_ok_", ""))
    r = await api.moliya_dokon_tolov_confirm(update.effective_user.id, sorov_id)
    if r.status_code == 200:
        await _edit(query, "✅ To'lov tasdiqlandi. So'rov Menejerга uzatildi.")
    else:
        await _edit(query, f"❌ Xatolik: {r.text[:200]}")


# ---------------------------------------------------------------------------
# Umumiy hisobot
# ---------------------------------------------------------------------------
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    from datetime import datetime

    d = await api.moliya_report(update.effective_user.id)
    if not d:
        await update.effective_message.reply_text("Hisobot olinmadi.")
        return
    sana = datetime.now().strftime("%d.%m.%Y")
    text = (
        f"📊 Umumiy holat — {sana}\n\n"
        f"💰 Jami mijozlar balansi: {d['jami_mijozlar_balansi']:,.0f} som\n"
        f"🏪 Jami adminlar kutilayotgan balansi: {d['jami_adminlar_balansi']:,.0f} som\n"
        f"🏦 Platforma hisobida (real pul) bo'lishi kerak: "
        f"~{d['platforma_hisobida']:,.0f} som\n\n"
        f"Bugungi harakatlar:\n"
        f"+ To'ldirishlar: {d['bugun_toldirish_summa']:,.0f} som "
        f"({d['bugun_toldirish_soni']} ta so'rov)\n"
        f"- Xaridlar: {d['bugun_xarid_summa']:,.0f} som "
        f"({d['bugun_xarid_soni']} ta buyurtma)\n"
        f"- Pul yechishlar: {d['bugun_yechish_summa']:,.0f} som "
        f"({d['bugun_yechish_soni']} ta so'rov)\n"
        f"- Komissiya yig'ildi: {d['bugun_komissiya']:,.0f} som"
    )
    await update.effective_message.reply_text(text)


# ---------------------------------------------------------------------------
# 💳 To'lov usullari boshqaruvi (task_2)
# ---------------------------------------------------------------------------
def _usul_row_kb(usul: dict) -> InlineKeyboardMarkup:
    faol = usul.get("faol")
    toggle_txt = "🔴 Nofaol qilish" if faol else "🟢 Faollashtirish"
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✏️ Tahrirlash", callback_data=f"med_{usul['id']}"),
                InlineKeyboardButton(toggle_txt, callback_data=f"mtog_{usul['id']}"),
            ],
            [InlineKeyboardButton("🗑 O'chirish", callback_data=f"mdel_{usul['id']}")],
        ]
    )


def _usul_line(usul: dict) -> str:
    emoji = _TURI_EMOJI.get(usul.get("turi"), "💰")
    holat = "🟢 faol" if usul.get("faol") else "🔴 nofaol"
    qiymat = f" — {usul['qiymat']}" if usul.get("qiymat") else ""
    return f"{emoji} <b>{usul.get('nomi')}</b>{qiymat} ({holat})"


async def methods(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    rows = await api.moliya_tolov_usullari(update.effective_user.id)
    await update.effective_message.reply_text(
        "💳 To'lov usullari" + ("" if rows else "\n\nHozircha usul yo'q."),
        reply_markup=cancel_kb_f(),
    )
    for u in rows:
        await update.effective_message.reply_text(
            _usul_line(u), parse_mode="HTML", reply_markup=_usul_row_kb(u)
        )
    await update.effective_message.reply_text(
        "➕ Yangi to'lov usuli qo'shish:",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("➕ Yangi usul qo'shish", callback_data="madd")]]
        ),
    )


async def method_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_super(update.effective_user.id):
        await query.answer("Faqat super-admin.", show_alert=True)
        return
    await query.answer()
    usul_id = int(query.data.replace("mtog_", ""))
    r = await api.moliya_toggle_tolov(update.effective_user.id, usul_id)
    if r.status_code == 200:
        u = r.json()
        await _edit(query, _usul_line(u))
        try:
            await query.edit_message_reply_markup(reply_markup=_usul_row_kb(u))
        except Exception:  # noqa: BLE001
            pass
    else:
        await _edit(query, f"❌ Xatolik: {r.text[:200]}")


async def method_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_super(update.effective_user.id):
        await query.answer("Faqat super-admin.", show_alert=True)
        return
    await query.answer()
    usul_id = int(query.data.replace("mdel_", ""))
    r = await api.moliya_delete_tolov(update.effective_user.id, usul_id)
    await _edit(query, "🗑 O'chirildi." if r.status_code == 200 else f"❌ {r.text[:200]}")


# --- Yangi usul qo'shish ---
async def method_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not _is_super(update.effective_user.id):
        await query.answer("Faqat super-admin.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("💳 Karta", callback_data="mnew_karta"),
                InlineKeyboardButton("📱 Telefon", callback_data="mnew_telefon"),
            ],
            [
                InlineKeyboardButton("🔳 QR kod", callback_data="mnew_qr_kod"),
                InlineKeyboardButton("₿ Crypto", callback_data="mnew_crypto"),
            ],
        ]
    )
    await query.message.reply_text("Yangi usul turini tanlang:", reply_markup=kb)
    return M_TURI


async def method_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    turi = query.data.replace("mnew_", "")
    context.user_data["m"] = {"turi": turi, "step": 0, "data": {}}
    field, prompt = _FIELD_SEQ[turi][0]
    await query.message.reply_text(
        prompt,
        reply_markup=cancel_kb_f(),
    )
    return M_STEP


async def method_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == BTN_HOME:
        context.user_data.pop("m", None)
        return await _to_menu(update)
    m = context.user_data.get("m")
    if not m:
        return ConversationHandler.END
    turi = m["turi"]
    seq = _FIELD_SEQ[turi]
    field, _ = seq[m["step"]]
    m["data"][field] = update.message.text.strip()
    m["step"] += 1

    if m["step"] < len(seq):
        _, prompt = seq[m["step"]]
        await update.effective_message.reply_text(prompt)
        return M_STEP
    # Maydonlar tugadi.
    if turi == "qr_kod":
        await update.effective_message.reply_text("🔳 QR kod rasmini yuboring:")
        return M_QR
    return await _method_save(update, context)


async def method_qr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text and update.message.text == BTN_HOME:
        context.user_data.pop("m", None)
        return await _to_menu(update)
    if not update.message.photo:
        await update.effective_message.reply_text("Iltimos, QR kod RASMINI yuboring:")
        return M_QR
    file_id = update.message.photo[-1].file_id
    context.user_data["m"]["data"]["qr_rasm_url"] = f"/media/{file_id}"
    return await _method_save(update, context)


async def _method_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    m = context.user_data.pop("m", None)
    if not m:
        return ConversationHandler.END
    payload = {"turi": m["turi"], **m["data"]}
    r = await api.moliya_create_tolov(update.effective_user.id, payload)
    msg = (
        "✅ To'lov usuli qo'shildi!"
        if r.status_code == 200
        else f"❌ Xatolik: {r.text[:200]}"
    )
    await update.effective_message.reply_text(msg, reply_markup=menu_markup())
    return ConversationHandler.END


# --- Usulni tahrirlash (nomi + qiymat) ---
async def method_edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not _is_super(update.effective_user.id):
        await query.answer("Faqat super-admin.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    context.user_data["edit_usul"] = int(query.data.replace("med_", ""))
    await query.message.reply_text(
        "✏️ Yangi nomni kiriting (o'zgartirmaslik uchun '-'):",
        reply_markup=cancel_kb_f(),
    )
    return ME_NOMI


async def method_edit_nomi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == BTN_HOME:
        return await _to_menu(update)
    matn = update.message.text.strip()
    context.user_data["edit_nomi"] = None if matn == "-" else matn
    await update.effective_message.reply_text("Yangi qiymatni kiriting (karta/tel/manzil), '-' = o'zgartirmaslik:")
    return ME_QIYMAT


async def method_edit_qiymat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == BTN_HOME:
        return await _to_menu(update)
    matn = update.message.text.strip()
    usul_id = context.user_data.pop("edit_usul", None)
    data = {}
    nomi = context.user_data.pop("edit_nomi", None)
    if nomi:
        data["nomi"] = nomi
    if matn != "-":
        data["qiymat"] = matn
    if not data:
        await update.effective_message.reply_text("O'zgarish yo'q.", reply_markup=menu_markup())
        return ConversationHandler.END
    r = await api.moliya_update_tolov(update.effective_user.id, usul_id, data)
    msg = "✅ Yangilandi." if r.status_code == 200 else f"❌ {r.text[:200]}"
    await update.effective_message.reply_text(msg, reply_markup=menu_markup())
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Yordamchilar
# ---------------------------------------------------------------------------
def _base_url() -> str:
    import os

    return (
        os.getenv("WEBHOOK_BASE_URL", "").strip()
        or os.getenv("RENDER_EXTERNAL_URL", "").strip()
    ).rstrip("/")


async def _edit(query, text: str) -> None:
    try:
        if query.message and query.message.photo:
            await query.edit_message_caption(caption=text)
        else:
            await query.edit_message_text(text)
    except Exception:  # noqa: BLE001
        await query.message.reply_text(text)


async def _to_menu(update: Update) -> int:
    await update.effective_message.reply_text("Bosh menyu 👇", reply_markup=menu_markup())
    return ConversationHandler.END


def build_application(token: str) -> Application:
    app = Application.builder().token(token).updater(None).build()

    TXT = filters.TEXT & ~filters.COMMAND

    conv_cancel = CallbackQueryHandler(cancel_conv_f, pattern="^conv:cancel$")
    # Rad etish sababi (to'ldirish/qaytarish) — callbackдан kiradi.
    reject_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(reject_start, pattern="^mt_no_"),
            CallbackQueryHandler(reject_start, pattern="^mr_no_"),
            CallbackQueryHandler(reject_start, pattern="^dt_no_"),
        ],
        states={R_SABAB: [MessageHandler(TXT, reject_reason)]},
        fallbacks=[CommandHandler("start", start), conv_cancel],
        name="moliya_reject",
        persistent=False,
    )
    # Yangi to'lov usuli qo'shish (turini tanlash -> maydonlar -> saqlash).
    method_add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(method_add_start, pattern="^madd$")],
        states={
            M_TURI: [CallbackQueryHandler(method_type, pattern="^mnew_")],
            M_STEP: [MessageHandler(TXT, method_step)],
            M_QR: [
                MessageHandler(filters.PHOTO, method_qr),
                MessageHandler(TXT, method_qr),
            ],
        },
        fallbacks=[CommandHandler("start", start), conv_cancel],
        name="moliya_method_add",
        persistent=False,
    )
    # Usulni tahrirlash (nomi + qiymat).
    method_edit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(method_edit_start, pattern="^med_")],
        states={
            ME_NOMI: [MessageHandler(TXT, method_edit_nomi)],
            ME_QIYMAT: [MessageHandler(TXT, method_edit_qiymat)],
        },
        fallbacks=[CommandHandler("start", start), conv_cancel],
        name="moliya_method_edit",
        persistent=False,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(reject_conv)
    app.add_handler(method_add_conv)
    app.add_handler(method_edit_conv)
    # Inline menyu (Menyu_Inline_Prompt).
    app.add_handler(CallbackQueryHandler(menu_home_f, pattern="^fm:home$"))
    app.add_handler(CallbackQueryHandler(
        menu_router_f,
        pattern="^fm:(topups|withdraws|refunds|dokon_tolov|report|methods)$",
    ))

    # Inline callbacklar (menyu ro'yxati va push xabarlaridан).
    app.add_handler(CallbackQueryHandler(topup_approve, pattern="^mt_ok_"))
    app.add_handler(CallbackQueryHandler(withdraw_paid, pattern="^mw_ok_"))
    app.add_handler(CallbackQueryHandler(refund_approve, pattern="^mr_ok_"))
    app.add_handler(CallbackQueryHandler(dokon_tolov_confirm, pattern="^dt_ok_"))
    app.add_handler(CallbackQueryHandler(method_toggle, pattern="^mtog_"))
    app.add_handler(CallbackQueryHandler(method_delete, pattern="^mdel_"))
    return app
