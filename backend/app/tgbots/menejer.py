"""Menejer Boti — faqat MENEJER_ID ro'yxatidagilar (rule 2).

Do'kon so'rovlari, adminlar, do'kon/mahsulot o'chirish, arenda nazorati va
hisobot. Boshqaruv Bot bilan umumiy kod yo'q — faqat umumiy baza (backend).
Barcha summalar KGS (Qirg'iziston somi).
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

logger = logging.getLogger("arzon.menejer")

BTN_SOROVLAR = "🏪 Do'kon so'rovlari"
BTN_ADMINLAR = "👤 Adminlar"
BTN_DOKON_OCHIR = "🗑 Do'kon o'chirish"
BTN_MAHSULOT_OCHIR = "🗑 Mahsulot o'chirish"
BTN_ARENDA = "💰 Arenda nazorati"
BTN_XABAR = "📢 Xabar yuborish"
BTN_REPORT = "📊 Hisobot"
BTN_HOME = "🏠 Bosh menyu"

MD_SABAB, ADD_TID, BC_CHOOSE, BC_TEXT = range(4)


def _is_menejer(uid: int) -> bool:
    return uid in settings.menejer_id_list


def _base_url() -> str:
    import os

    return (
        os.getenv("WEBHOOK_BASE_URL", "").strip()
        or os.getenv("RENDER_EXTERNAL_URL", "").strip()
    ).rstrip("/")


def menu_markup() -> InlineKeyboardMarkup:
    # Inline menyu (Menyu_Inline_Prompt) — xabarга biriktiriladi.
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(BTN_SOROVLAR, callback_data="mm:sorovlar"),
             InlineKeyboardButton(BTN_ADMINLAR, callback_data="mm:adminlar")],
            [InlineKeyboardButton(BTN_DOKON_OCHIR, callback_data="mm:dokon_ochir"),
             InlineKeyboardButton(BTN_MAHSULOT_OCHIR, callback_data="mm:mahsulot_ochir")],
            [InlineKeyboardButton(BTN_XABAR, callback_data="mm:xabar"),
             InlineKeyboardButton(BTN_ARENDA, callback_data="mm:arenda")],
            [InlineKeyboardButton(BTN_REPORT, callback_data="mm:report")],
        ]
    )


def back_home_m() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Bosh menyu", callback_data="mm:home")]]
    )


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Bekor qilish", callback_data="conv:cancel")]]
    )


async def menu_home_m(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    try:
        await q.edit_message_text(
            "🧑‍💼 ARZON Menejer Boti\n\nPlatformani boshqaring 👇",
            reply_markup=menu_markup(),
        )
    except Exception:  # noqa: BLE001
        await update.effective_message.reply_text(
            "Bosh menyu 👇", reply_markup=menu_markup()
        )


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inline menyu tugmalarini tegishli handlerга yo'naltiradi."""
    q = update.callback_query
    await q.answer()
    key = q.data.split(":", 1)[1]
    fn = {
        "sorovlar": sorovlar, "adminlar": adminlar,
        "dokon_ochir": dokon_ochirish, "mahsulot_ochir": mahsulot_ochirish,
        "arenda": arenda, "report": report,
    }.get(key)
    if fn:
        await fn(update, context)


async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    context.user_data.clear()
    await update.effective_message.reply_text(
        "❌ Bekor qilindi. Bosh menyu 👇", reply_markup=menu_markup()
    )
    return ConversationHandler.END


async def _guard(update: Update) -> bool:
    if not _is_menejer(update.effective_user.id):
        await update.effective_message.reply_text(
            "⛔️ Sizda bu botdan foydalanish huquqi yo'q."
        )
        return False
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    # Eski pastki (reply) klaviaturани olib tashlaymiz — endi faqat inline menyu.
    await update.effective_message.reply_text(
        "🧑‍💼 ARZON Menejer Boti", reply_markup=ReplyKeyboardRemove()
    )
    await update.effective_message.reply_text(
        "Platformani boshqaring 👇", reply_markup=menu_markup()
    )


async def _edit(query, text, reply_markup=None):
    try:
        if query.message and query.message.photo:
            await query.edit_message_caption(caption=text, reply_markup=reply_markup)
        else:
            await query.edit_message_text(text, reply_markup=reply_markup)
    except Exception:  # noqa: BLE001
        await query.message.reply_text(text, reply_markup=reply_markup)


# ---------------------------------------------------------------------------
# 🏪 Do'kon so'rovlari
# ---------------------------------------------------------------------------
async def sorovlar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    uid = update.effective_user.id
    rows = await api.menejer_dokon_sorovlari(uid)
    if not rows:
        await update.effective_message.reply_text("Kutilayotgan do'kon so'rovi yo'q. ✅")
        return
    xmap = {"mos_keladi": "✅ Mos", "mos_kelmaydi": "⚠️ Mos emas", "aniq_emas": "❓"}
    for s in rows[:20]:
        ai = (
            f"🤖 Gemini: {s['ai_summa']:,.0f} som"
            if s.get("ai_summa") is not None
            else "🤖 Gemini: o'qilmadi"
        )
        text = (
            f"🏪 Yangi do'kon so'rovi #{s['id']}\n"
            f"Nomi: {s['dokon_nomi']}\n"
            f"Egasi: {s.get('ism') or 'nomalum'}, {s.get('telegram_id')}\n"
            f"Admin ID: {s['admin_telegram_id']}\n"
            f"Mahsulotlar soni: {s['mahsulot_soni']} ta\n"
            f"Ochish to'lovi: {s['summa']:,.0f} som\n"
            f"{ai} — {xmap.get(s.get('ai_xulosa'), '❓')}"
        )
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"md_ok_{s['id']}"),
                    InlineKeyboardButton("❌ Rad etish", callback_data=f"md_no_{s['id']}"),
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


async def approve_do(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Do'kon ochishни tasdiqlaydi. Arenda avtomatik (mahsulot soniга qarab)."""
    query = update.callback_query
    if not _is_menejer(update.effective_user.id):
        await query.answer("Ruxsat yo'q.", show_alert=True)
        return
    await query.answer()
    sorov_id = int(query.data.replace("md_ok_", ""))
    r = await api.menejer_dokon_approve(update.effective_user.id, sorov_id)
    if r.status_code == 200:
        d = r.json()
        await _edit(
            query,
            f"✅ Do'kon ochildi: {d['nomi']}\n🔑 Kod: {d['mahfiy_kirish_kodi']}\n"
            "So'rovchiga havola, kod va oylik arenda yuborildi.",
        )
    else:
        await _edit(query, f"❌ {r.text[:200]}")


async def reject_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not _is_menejer(update.effective_user.id):
        await query.answer("Ruxsat yo'q.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    context.user_data["md_id"] = int(query.data.replace("md_no_", ""))
    await query.message.reply_text(
        "❌ Rad etish sababini yozing (so'rovchiga boradi):", reply_markup=cancel_kb()
    )
    return MD_SABAB


async def reject_sabab(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    sorov_id = context.user_data.pop("md_id", None)
    r = await api.menejer_dokon_reject(
        update.effective_user.id, sorov_id, update.message.text.strip()
    )
    msg = "✅ Rad etildi." if r.status_code == 200 else f"❌ {r.text[:200]}"
    await update.effective_message.reply_text(msg, reply_markup=menu_markup())
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# 👤 Adminlar
# ---------------------------------------------------------------------------
def _admin_kb(s: dict) -> InlineKeyboardMarkup:
    rows = []
    for tid in s.get("admin_ids", []):
        rows.append(
            [InlineKeyboardButton(f"🗑 Adminlikdan chiqarish: {tid}",
                                  callback_data=f"marm_{s['id']}_{tid}")]
        )
    rows.append([InlineKeyboardButton("➕ Admin qo'shish", callback_data=f"madd_{s['id']}")])
    return InlineKeyboardMarkup(rows)


async def adminlar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    rows = await api.menejer_adminlar(update.effective_user.id)
    if not rows:
        await update.effective_message.reply_text("Do'konlar yo'q.")
        return
    for s in rows[:30]:
        adm = ", ".join(str(a) for a in s.get("admin_ids", [])) or "yo'q"
        text = f"🏪 {s['nomi']} (ID {s['id']})\n👤 Adminlar: {adm}"
        await update.effective_message.reply_text(text, reply_markup=_admin_kb(s))


async def admin_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_menejer(update.effective_user.id):
        await query.answer("Ruxsat yo'q.", show_alert=True)
        return
    await query.answer()
    _, store_id, tid = query.data.split("_")
    r = await api.menejer_remove_admin(update.effective_user.id, int(store_id), int(tid))
    await _edit(query, "✅ Adminlikdan chiqarildi." if r.status_code == 200 else f"❌ {r.text[:150]}")


async def admin_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not _is_menejer(update.effective_user.id):
        await query.answer("Ruxsat yo'q.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    context.user_data["add_store"] = int(query.data.replace("madd_", ""))
    await query.message.reply_text(
        "Yangi adminning Telegram ID'sini kiriting:", reply_markup=cancel_kb()
    )
    return ADD_TID


async def admin_add_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    matn = update.message.text.strip()
    if not matn.isdigit():
        await update.effective_message.reply_text("Telegram ID raqam bo'lishi kerak:")
        return ADD_TID
    store_id = context.user_data.pop("add_store", None)
    r = await api.menejer_add_admin(update.effective_user.id, store_id, int(matn))
    msg = f"✅ Admin {matn} qo'shildi." if r.status_code == 200 else f"❌ {r.text[:150]}"
    await update.effective_message.reply_text(msg, reply_markup=menu_markup())
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# 🗑 Do'kon o'chirish (moderatsiya) — mahsulot o'chirishдан alohida
# ---------------------------------------------------------------------------
async def dokon_ochirish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    rows = await api.menejer_stores(update.effective_user.id)
    if not rows:
        await update.effective_message.reply_text("Do'konlar yo'q.")
        return
    await update.effective_message.reply_text("🗑 <b>Do'kon o'chirish</b> — do'konni tanlang:",
                                    parse_mode="HTML")
    for s in rows[:30]:
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🗑 Do'konni o'chirish", callback_data=f"mds_{s['id']}")]]
        )
        await update.effective_message.reply_text(
            f"🏪 {s['nomi']} (ID {s['id']}) — {s['mahsulot_soni']} mahsulot",
            reply_markup=kb,
        )


# ---------------------------------------------------------------------------
# 🗑 Mahsulot o'chirish (moderatsiya) — do'kon o'chirishдан alohida
# ---------------------------------------------------------------------------
async def mahsulot_ochirish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    rows = await api.menejer_stores(update.effective_user.id)
    if not rows:
        await update.effective_message.reply_text("Do'konlar yo'q.")
        return
    await update.effective_message.reply_text(
        "🗑 <b>Mahsulot o'chirish</b> — avval do'konni tanlang, keyin mahsulotni:",
        parse_mode="HTML",
    )
    for s in rows[:30]:
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("📦 Mahsulotlar", callback_data=f"mpr_{s['id']}")]]
        )
        await update.effective_message.reply_text(
            f"🏪 {s['nomi']} (ID {s['id']}) — {s['mahsulot_soni']} mahsulot",
            reply_markup=kb,
        )


async def store_del_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_menejer(update.effective_user.id):
        await query.answer("Ruxsat yo'q.", show_alert=True)
        return
    await query.answer()
    store_id = query.data.replace("mds_", "")
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Ha, o'chirilsin", callback_data=f"mdsok_{store_id}"),
                InlineKeyboardButton("❌ Yo'q", callback_data="mcancel"),
            ]
        ]
    )
    await _edit(query, "⚠️ Rostdan o'chirilsinmi? Bu qaytarib bo'lmaydi!", kb)


async def store_del_do(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_menejer(update.effective_user.id):
        await query.answer("Ruxsat yo'q.", show_alert=True)
        return
    await query.answer()
    store_id = int(query.data.replace("mdsok_", ""))
    r = await api.menejer_delete_store(update.effective_user.id, store_id)
    await _edit(query, f"🗑 O'chirildi: {r.json().get('nomi')}" if r.status_code == 200 else f"❌ {r.text[:150]}")


async def store_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_menejer(update.effective_user.id):
        await query.answer("Ruxsat yo'q.", show_alert=True)
        return
    await query.answer()
    store_id = int(query.data.replace("mpr_", ""))
    items = await api.menejer_store_products(update.effective_user.id, store_id)
    if not items:
        await query.message.reply_text("Bu do'konда mahsulot yo'q.")
        return
    for p in items[:40]:
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🗑 O'chirish", callback_data=f"mdp_{p['id']}")]]
        )
        await query.message.reply_text(
            f"📦 {p['nomi']} — {p['narxi']:,.0f} som", reply_markup=kb
        )


async def product_del(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_menejer(update.effective_user.id):
        await query.answer("Ruxsat yo'q.", show_alert=True)
        return
    await query.answer()
    product_id = int(query.data.replace("mdp_", ""))
    r = await api.menejer_delete_product(update.effective_user.id, product_id)
    await _edit(query, f"🗑 O'chirildi: {r.json().get('nomi')}" if r.status_code == 200 else f"❌ {r.text[:150]}")


async def cancel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await _edit(query, "Bekor qilindi.")


# ---------------------------------------------------------------------------
# 💰 Arenda nazorati
# ---------------------------------------------------------------------------
async def arenda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    from datetime import datetime, timezone

    rows = await api.menejer_arenda(update.effective_user.id)
    if not rows:
        await update.effective_message.reply_text("Do'konlar yo'q.")
        return
    now = datetime.now(timezone.utc)
    for s in rows[:30]:
        holat = "🟢 Faol" if s["holat"] == "faol" else "🔴 To'xtatilgan"
        arenda_txt = (
            f"{s['arenda_summasi']:,.0f} som/oy" if s.get("arenda_summasi") else "yo'q"
        )
        muddat = s.get("arenda_muddati_tugashi")
        muddat_txt = "—"
        if muddat:
            try:
                d = datetime.fromisoformat(muddat)
                qolgan = (d - now).days
                muddat_txt = f"{d.strftime('%d.%m.%Y')} ({qolgan} kun)"
            except Exception:  # noqa: BLE001
                muddat_txt = muddat
        text = (
            f"🏪 {s['nomi']} (ID {s['id']})\n"
            f"Holat: {holat}\n"
            f"Arenda: {arenda_txt}\n"
            f"Muddat: {muddat_txt}"
        )
        btns = [
            InlineKeyboardButton("✅ Arenda uzaytir (1 oy)", callback_data=f"max_{s['id']}")
        ]
        if s["holat"] == "faol":
            btns2 = [InlineKeyboardButton("🔴 Bloklash", callback_data=f"mab_{s['id']}")]
        else:
            btns2 = [InlineKeyboardButton("🟢 Blokdan chiqarish", callback_data=f"mau_{s['id']}")]
        await update.effective_message.reply_text(
            text, reply_markup=InlineKeyboardMarkup([btns, btns2])
        )


async def arenda_extend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_menejer(update.effective_user.id):
        await query.answer("Ruxsat yo'q.", show_alert=True)
        return
    await query.answer()
    store_id = int(query.data.replace("max_", ""))
    r = await api.menejer_arenda_uzaytir(update.effective_user.id, store_id)
    await _edit(query, "✅ Arenda 1 oyга uzaytirildi, do'kon faol." if r.status_code == 200 else f"❌ {r.text[:150]}")


async def arenda_block(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_menejer(update.effective_user.id):
        await query.answer("Ruxsat yo'q.", show_alert=True)
        return
    await query.answer()
    store_id = int(query.data.replace("mab_", ""))
    r = await api.menejer_block(update.effective_user.id, store_id)
    await _edit(query, "🔴 Do'kon bloklandi (admin bot kirishi to'xtatildi)." if r.status_code == 200 else f"❌ {r.text[:150]}")


async def arenda_unblock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_menejer(update.effective_user.id):
        await query.answer("Ruxsat yo'q.", show_alert=True)
        return
    await query.answer()
    store_id = int(query.data.replace("mau_", ""))
    r = await api.menejer_unblock(update.effective_user.id, store_id)
    await _edit(query, "🟢 Do'kon blokdan chiqarildi." if r.status_code == 200 else f"❌ {r.text[:150]}")


# ---------------------------------------------------------------------------
# 📊 Hisobot (Moliyadан bir xil ma'lumot)
# ---------------------------------------------------------------------------
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    from datetime import datetime

    d = await api.menejer_report(update.effective_user.id)
    if not d:
        await update.effective_message.reply_text("Hisobot olinmadi.")
        return
    sana = datetime.now().strftime("%d.%m.%Y")
    text = (
        f"📊 <b>Umumiy holat</b> — {sana}\n\n"
        f"💰 Mijozlar balansi: <b>{d['jami_mijozlar_balansi']:,.0f} som</b>\n"
        f"🏪 Adminlar balansi: <b>{d['jami_adminlar_balansi']:,.0f} som</b>\n"
        f"🏦 Platforma hisobida: <b>~{d['platforma_hisobida']:,.0f} som</b>\n\n"
        f"📅 <b>Bugungi harakatlar:</b>\n"
        f"➕ To'ldirish: <b>{d['bugun_toldirish_summa']:,.0f} som</b> ({d['bugun_toldirish_soni']} ta)\n"
        f"🛍 Xaridlar: <b>{d['bugun_xarid_summa']:,.0f} som</b> ({d['bugun_xarid_soni']} ta)\n"
        f"➖ Pul yechish: <b>{d['bugun_yechish_summa']:,.0f} som</b> ({d['bugun_yechish_soni']} ta)\n"
        f"🪙 Komissiya: <b>{d['bugun_komissiya']:,.0f} som</b>"
    )
    await update.effective_message.reply_text(text, parse_mode="HTML")


# ---------------------------------------------------------------------------
# 📢 Xabar yuborish (adminlarга yoki mijozларга)
# ---------------------------------------------------------------------------
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    if not await _guard(update):
        return ConversationHandler.END
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("👨‍💼 Adminlarga", callback_data="bc_admin")],
            [InlineKeyboardButton("🛍 Mijozlarga", callback_data="bc_customer")],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="conv:cancel")],
        ]
    )
    await update.effective_message.reply_text(
        "📢 Xabar kimga yuborilsin?", reply_markup=kb
    )
    return BC_CHOOSE


async def broadcast_choose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    target = query.data.replace("bc_", "")
    context.user_data["bc_target"] = target
    nomi = "adminlarga (Boshqaruv bot)" if target == "admin" else "mijozlarga (Savdo bot)"
    await query.message.reply_text(
        f"✍️ {nomi} yuboriladigan xabar matnini yozing:", reply_markup=cancel_kb()
    )
    return BC_TEXT


async def broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target = context.user_data.pop("bc_target", None)
    if not target:
        return ConversationHandler.END
    matn = update.message.text
    await update.effective_message.reply_text("⏳ Yuborilmoqda...")
    r = await api.menejer_broadcast(update.effective_user.id, target, matn)
    if r.status_code == 200:
        d = r.json()
        await update.effective_message.reply_text(
            f"✅ Xabar {d['yuborildi']} ta foydalanuvchiga yuborildi.",
            reply_markup=menu_markup(),
        )
    else:
        await update.effective_message.reply_text(f"❌ {r.text[:200]}", reply_markup=menu_markup())
    return ConversationHandler.END


def build_application(token: str) -> Application:
    app = Application.builder().token(token).updater(None).build()
    TXT = filters.TEXT & ~filters.COMMAND

    conv_cancel = CallbackQueryHandler(cancel_conv, pattern="^conv:cancel$")
    reject_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(reject_start, pattern="^md_no_")],
        states={MD_SABAB: [MessageHandler(TXT, reject_sabab)]},
        fallbacks=[CommandHandler("start", start), conv_cancel],
        name="menejer_reject", persistent=False,
    )
    addadmin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_start, pattern="^madd_")],
        states={ADD_TID: [MessageHandler(TXT, admin_add_id)]},
        fallbacks=[CommandHandler("start", start), conv_cancel],
        name="menejer_addadmin", persistent=False,
    )
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(broadcast_start, pattern="^mm:xabar$")],
        states={
            BC_CHOOSE: [CallbackQueryHandler(broadcast_choose, pattern="^bc_")],
            BC_TEXT: [MessageHandler(TXT, broadcast_text)],
        },
        fallbacks=[CommandHandler("start", start), conv_cancel],
        name="menejer_broadcast", persistent=False,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(reject_conv)
    app.add_handler(addadmin_conv)
    app.add_handler(broadcast_conv)
    # Do'kon tasdiqlash — to'g'ridan-to'g'ri (arenda avtomatik).
    app.add_handler(CallbackQueryHandler(approve_do, pattern="^md_ok_"))
    # Inline menyu (Menyu_Inline_Prompt).
    app.add_handler(CallbackQueryHandler(menu_home_m, pattern="^mm:home$"))
    app.add_handler(CallbackQueryHandler(
        menu_router,
        pattern="^mm:(sorovlar|adminlar|dokon_ochir|mahsulot_ochir|arenda|report)$",
    ))

    app.add_handler(CallbackQueryHandler(admin_remove, pattern="^marm_"))
    app.add_handler(CallbackQueryHandler(store_del_confirm, pattern="^mds_"))
    app.add_handler(CallbackQueryHandler(store_del_do, pattern="^mdsok_"))
    app.add_handler(CallbackQueryHandler(store_products, pattern="^mpr_"))
    app.add_handler(CallbackQueryHandler(product_del, pattern="^mdp_"))
    app.add_handler(CallbackQueryHandler(cancel_cb, pattern="^mcancel$"))
    app.add_handler(CallbackQueryHandler(arenda_extend, pattern="^max_"))
    app.add_handler(CallbackQueryHandler(arenda_block, pattern="^mab_"))
    app.add_handler(CallbackQueryHandler(arenda_unblock, pattern="^mau_"))
    return app
