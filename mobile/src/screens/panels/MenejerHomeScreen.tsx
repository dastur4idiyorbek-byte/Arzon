/**
 * Menejer paneli (4.3) — do'kon so'rovlari, do'konlar + arenda, hisobot.
 * Faqat menejer roli.
 */
import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, Alert, TouchableOpacity } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { api, money } from "../../api";
import { colors, radius, spacing, font } from "../../theme";
import { Screen, Card, Btn, Loader, Empty, Field } from "./PanelUI";
import { PanelHome, BolimSarlavha, PanelBolim } from "./PanelHome";
import { usePrompt } from "../../ui/Prompt";

const BOLIMLAR: PanelBolim[] = [
  { key: "sorovlar", label: "Do'kon so'rovlari", izoh: "Yangi do'kon ochish arizalari",
    icon: "storefront-outline", rang: colors.brand },
  { key: "dokonlar", label: "Do'konlar va arenda", izoh: "Adminlar, bloklash, arendani uzaytirish",
    icon: "business-outline", rang: colors.store },
  { key: "report", label: "Hisobot", izoh: "Platforma umumiy holati",
    icon: "stats-chart-outline", rang: colors.gold },
];

const NOM: Record<string, string> = Object.fromEntries(
  BOLIMLAR.map((b) => [b.key, b.label])
);

export default function MenejerHomeScreen() {
  const [tab, setTab] = useState<string | null>(null);
  const [rows, setRows] = useState<any[]>([]);
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const prompt = usePrompt();

  const load = useCallback(async () => {
    if (tab === null) { setLoading(false); return; }
    setLoading(true);
    if (tab === "report") {
      const { ok, data } = await api("/api/menejer/report");
      setReport(ok ? data : null);
    } else {
      const path = tab === "sorovlar" ? "/api/menejer/dokon-sorovlari" : "/api/menejer/stores";
      const { ok, data } = await api(path);
      setRows(ok && Array.isArray(data) ? (data as any[]) : []);
    }
    setLoading(false);
  }, [tab]);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  async function act(path: string, body?: any, muvaffaqiyat = "Bajarildi") {
    setBusy(true);
    const { ok, status, data } = await api(path, { method: "POST", body });
    setBusy(false);
    if (ok) {
      Alert.alert("✅ " + muvaffaqiyat, "");
      load();
    } else {
      Alert.alert(
        "Xatolik",
        (data as any)?.detail ||
          (status === 0 ? "Internet yo'q yoki server javob bermadi." : `Xato kodi: ${status}`)
      );
    }
  }

  async function reject(path: string) {
    const sabab = await prompt({
      title: "Rad etish",
      message: "Sababini yozing (bo'sh qoldirsangiz ham bo'ladi):",
      placeholder: "Masalan: hujjat to'liq emas",
      submitLabel: "Rad etish",
      multiline: true,
    });
    if (sabab === null) return;
    act(path, { sabab: sabab.trim() }, "Rad etildi");
  }

  function arendaColor(s: any) {
    if (s.holat === "bloklangan") return colors.sale;
    if (s.holat === "faol") return colors.store;
    return colors.textMuted;
  }

  /** Adminlar ro'yxati: ARZON ID + kirish usuli (backend "adminlar"da beradi). */
  function adminlar(s: any) {
    const list: any[] = s.adminlar || [];
    if (!list.length) return "yo'q";
    return list
      .map((a) => (a.arzon_id ? `#${a.arzon_id}` : `tg:${a.admin_id}`))
      .join(", ");
  }

  async function addAdmin(s: any) {
    const v = await prompt({
      title: "Admin qo'shish",
      message:
        `"${s.nomi}" uchun quyidagilardan birini kiriting:\n` +
        "• ARZON ID — masalan #42 (tavsiya)\n" +
        "• Email — ilovaga kirgan email\n" +
        "• Telegram ID — tg:123456789",
      placeholder: "#42",
      submitLabel: "Qo'shish",
    });
    const t = (v || "").trim();
    if (!t) return;
    // #42 yoki 42 -> ARZON ID; email -> email; "tg:12345" -> Telegram ID.
    let body: any;
    if (t.includes("@")) body = { email: t };
    else if (/^tg:\d+$/i.test(t)) body = { telegram_id: Number(t.slice(3)) };
    else {
      const n = Number(t.replace(/^#/, ""));
      if (!n) return Alert.alert("Xatolik", "ARZON ID raqam bo'lishi kerak (masalan #42).");
      body = { arzon_id: n };
    }
    act(`/api/menejer/stores/${s.id}/admins`, body, "Admin qo'shildi");
  }

  /** Do'konni BUTUNLAY o'chirish — mahsulotlari bilan. Qaytarib bo'lmaydi. */
  async function deleteStore(s: any) {
    const tasdiq = await prompt({
      title: "⚠️ Do'konni butunlay o'chirish",
      message:
        `"${s.nomi}" do'koni va uning BARCHA mahsulotlari o'chiriladi.\n` +
        "Bu amalni qaytarib bo'lmaydi!\n\n" +
        `Tasdiqlash uchun do'kon nomini aynan yozing:\n${s.nomi}`,
      placeholder: s.nomi,
      submitLabel: "O'chirish",
    });
    if (tasdiq === null) return;
    if (tasdiq.trim() !== s.nomi) {
      return Alert.alert("Bekor qilindi", "Do'kon nomi mos kelmadi — hech narsa o'chirilmadi.");
    }
    setBusy(true);
    const { ok, data } = await api(`/api/menejer/stores/${s.id}`, { method: "DELETE" });
    setBusy(false);
    if (ok) {
      Alert.alert("✅ O'chirildi", `"${s.nomi}" do'koni o'chirildi.`);
      load();
    } else {
      Alert.alert("Xatolik", (data as any)?.detail || "O'chirilmadi.");
    }
  }

  function removeAdmin(s: any, a: any) {
    Alert.alert("Adminni olib tashlash", `#${a.arzon_id ?? a.admin_id} — ishonchingiz komilmi?`, [
      { text: "Yo'q" },
      {
        text: "Ha",
        style: "destructive",
        onPress: async () => {
          const { ok } = await api(`/api/menejer/stores/${s.id}/admins/${a.admin_id}`, { method: "DELETE" });
          if (ok) load();
          else Alert.alert("Xatolik", "Olib tashlanmadi.");
        },
      },
    ]);
  }

  // Bosh sahifa — kartochkali menyu (Admin paneli kabi).
  if (tab === null) {
    return (
      <PanelHome
        sarlavha="Menejer paneli"
        izoh="Do'konlar, adminlar va arenda boshqaruvi"
        bolimlar={BOLIMLAR}
        onSelect={(k) => { setTab(k); setLoading(true); }}
      />
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.bgSoft }}>
      <BolimSarlavha matn={NOM[tab]} onBack={() => setTab(null)} />
      {loading ? (
        <Loader />
      ) : (
        <Screen>
          {tab === "report" && report && (
            <Card style={{ backgroundColor: "rgba(201,151,26,0.10)", borderColor: "rgba(201,151,26,0.35)" }}>
              <Text style={styles.h}>💰 Platforma hisobida</Text>
              <Text style={styles.big}>{money(report.platforma_hisobida)} som</Text>
              <Field label="Do'konlar hisobida" value={`${money(report.jami_adminlar_balansi)} som`} />
              <Field label="Bugun xaridlar" value={`${money(report.bugun_xarid_summa)} som`} />
              <Field label="Bugun komissiya" value={`${money(report.bugun_komissiya)} som`} />
            </Card>
          )}

          {tab === "sorovlar" && (rows.length === 0 ? <Empty text="Yangi do'kon so'rovi yo'q." /> :
            rows.map((s) => (
              <Card key={s.id}>
                <Text style={styles.name}>🏪 {s.dokon_nomi}</Text>
                <Text style={styles.muted}>{s.ism || `ID ${s.telegram_id}`}</Text>
                <Field label="Mahsulot soni" value={String(s.mahsulot_soni)} />
                <Field label="Arenda" value={`${money(s.summa)} som`} />
                {s.ai_summa != null && <Text style={styles.ai}>🤖 Chekda: {money(s.ai_summa)} som</Text>}
                <View style={styles.actions}>
                  <Btn label="✅ Tasdiqlash" tone="store" disabled={busy} style={{ flex: 1 }}
                    onPress={() => act(`/api/menejer/dokon-sorovlari/${s.id}/approve`, undefined, "Do'kon ochildi")} />
                  <Btn label="❌ Rad" tone="sale" disabled={busy} style={{ flex: 1 }}
                    onPress={() => reject(`/api/menejer/dokon-sorovlari/${s.id}/reject`)} />
                </View>
              </Card>
            )))}

          {tab === "dokonlar" && (rows.length === 0 ? <Empty text="Do'konlar yo'q." /> :
            rows.map((s) => (
              <Card key={s.id}>
                <View style={styles.head}>
                  <Text style={styles.name}>🏬 {s.nomi}</Text>
                  <Text style={[styles.holat, { color: arendaColor(s) }]}>{s.holat}</Text>
                </View>
                <Field label="Mahsulotlar" value={`${s.mahsulot_soni} / ${s.mahsulot_limiti}`} />
                {s.arenda_summasi != null && <Field label="Oylik arenda" value={`${money(s.arenda_summasi)} som`} />}
                <Field label="Adminlar" value={adminlar(s)} />
                {(s.adminlar || []).map((a: any) => (
                  <TouchableOpacity key={a.admin_id} style={styles.adminRow}
                    onPress={() => removeAdmin(s, a)}>
                    <Text style={styles.adminId}>
                      {a.arzon_id ? `#${a.arzon_id}` : `tg:${a.admin_id}`}
                    </Text>
                    <Text style={styles.adminName} numberOfLines={1}>
                      {a.ism || a.email || "—"}
                    </Text>
                    <Text style={styles.adminUsul}>
                      {a.usul === "ilova" ? "📱 ilova" : "✈️ Telegram"}
                    </Text>
                    <Text style={styles.adminDel}>✕</Text>
                  </TouchableOpacity>
                ))}
                <View style={styles.actions}>
                  <Btn label="💵 Arenda uzaytirish" tone="gold" disabled={busy} style={{ flex: 1 }}
                    onPress={() => act(`/api/menejer/stores/${s.id}/arenda-uzaytir`, undefined, "Arenda uzaytirildi")} />
                  {s.holat === "bloklangan" ? (
                    <Btn label="🔓 Blokdan chiqar" tone="store" disabled={busy} style={{ flex: 1 }}
                      onPress={() => act(`/api/menejer/stores/${s.id}/unblock`, undefined, "Blokdan chiqarildi")} />
                  ) : (
                    <Btn label="🔒 Bloklash" tone="sale" disabled={busy} style={{ flex: 1 }}
                      onPress={() => act(`/api/menejer/stores/${s.id}/block`, undefined, "Bloklandi")} />
                  )}
                </View>
                <View style={styles.actions}>
                  <Btn label="➕ Admin qo'shish" tone="ghost" disabled={busy}
                    style={{ flex: 1 }} onPress={() => addAdmin(s)} />
                  <Btn label="🗑 Do'konni o'chirish" tone="sale" disabled={busy}
                    style={{ flex: 1 }} onPress={() => deleteStore(s)} />
                </View>
              </Card>
            )))}
        </Screen>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  h: { fontSize: font.h2, fontWeight: "800", color: colors.text, marginBottom: 8 },
  big: { fontSize: 28, fontWeight: "800", color: colors.gold, marginBottom: 8 },
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  name: { fontWeight: "700", color: colors.store, fontSize: 15 },
  holat: { fontWeight: "700", fontSize: 12 },
  muted: { color: colors.textMuted, fontSize: 13, marginTop: 2 },
  ai: { color: colors.store, fontWeight: "600", marginTop: 4 },
  actions: { flexDirection: "row", gap: 8, marginTop: 12 },
  adminRow: {
    flexDirection: "row", alignItems: "center", gap: 8,
    paddingVertical: 6, borderTopWidth: 1, borderTopColor: colors.line,
  },
  adminId: { fontWeight: "800", color: colors.brand, minWidth: 44 },
  adminName: { flex: 1, color: colors.text, fontSize: 13 },
  adminUsul: { color: colors.textMuted, fontSize: 11 },
  adminDel: { color: colors.sale, fontWeight: "800", paddingHorizontal: 6 },
});
