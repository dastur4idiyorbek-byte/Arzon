/**
 * Moliya paneli (4.2) — to'ldirish/yechish/qaytarish so'rovlari + hisobot.
 * Faqat super-admin (moliya roli).
 */
import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, Alert } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { api, money } from "../../api";
import { colors, radius, spacing, font } from "../../theme";
import { Screen, Segmented, Card, Btn, Loader, Empty, Field } from "./PanelUI";
import { usePrompt } from "../../ui/Prompt";

const TABS = [
  { key: "topups", label: "💳 To'ldirish" },
  { key: "withdraws", label: "🏧 Yechish" },
  { key: "refunds", label: "↩️ Qaytarish" },
  { key: "report", label: "📊 Hisobot" },
];

export default function MoliyaHomeScreen() {
  const [tab, setTab] = useState("topups");
  const [rows, setRows] = useState<any[]>([]);
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const prompt = usePrompt();

  const load = useCallback(async () => {
    if (tab === "report") {
      const { ok, data } = await api("/api/moliya/report");
      setReport(ok ? data : null);
    } else {
      const { ok, data } = await api(`/api/moliya/${tab}`);
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
      placeholder: "Masalan: chek noto'g'ri",
      submitLabel: "Rad etish",
      multiline: true,
    });
    if (sabab === null) return; // bekor qilindi
    act(path, { sabab: sabab.trim() }, "Rad etildi");
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <Segmented items={TABS} value={tab} onChange={setTab} />
      {loading ? (
        <Loader />
      ) : (
        <Screen>
          {tab === "report" && report && (
            <>
              <Card style={{ backgroundColor: "rgba(201,151,26,0.10)", borderColor: "rgba(201,151,26,0.35)" }}>
                <Text style={styles.h}>💰 Platforma hisobida</Text>
                <Text style={styles.big}>{money(report.platforma_hisobida)} som</Text>
                <Field label="Mijozlar balansi" value={`${money(report.jami_mijozlar_balansi)} som`} />
                <Field label="Adminlar balansi" value={`${money(report.jami_adminlar_balansi)} som`} />
              </Card>
              <Card>
                <Text style={styles.h}>📅 Bugun</Text>
                <Field label="To'ldirish" value={`${money(report.bugun_toldirish_summa)} som (${report.bugun_toldirish_soni})`} />
                <Field label="Xaridlar" value={`${money(report.bugun_xarid_summa)} som (${report.bugun_xarid_soni})`} />
                <Field label="Pul yechish" value={`${money(report.bugun_yechish_summa)} som (${report.bugun_yechish_soni})`} />
                <Field label="Komissiya" value={`${money(report.bugun_komissiya)} som`} />
              </Card>
            </>
          )}

          {tab === "topups" && (rows.length === 0 ? <Empty text="Yangi so'rov yo'q." /> :
            rows.map((s) => (
              <Card key={s.id}>
                <Text style={styles.name}>{s.ism || `ID ${s.telegram_id}`}</Text>
                <Text style={styles.summa}>{money(s.summa)} som</Text>
                {s.ai_summa != null && <Text style={styles.ai}>🤖 Chekda: {money(s.ai_summa)} som</Text>}
                {!!s.ai_xulosa && <Text style={styles.muted}>{s.ai_xulosa}</Text>}
                <View style={styles.actions}>
                  <Btn label="✅ Tasdiqlash" tone="store" disabled={busy} style={{ flex: 1 }}
                    onPress={() => act(`/api/moliya/topups/${s.id}/approve`, undefined, "Balans to'ldirildi")} />
                  <Btn label="❌ Rad" tone="sale" disabled={busy} style={{ flex: 1 }}
                    onPress={() => reject(`/api/moliya/topups/${s.id}/reject`)} />
                </View>
              </Card>
            )))}

          {tab === "withdraws" && (rows.length === 0 ? <Empty text="Yangi so'rov yo'q." /> :
            rows.map((s) => (
              <Card key={s.id}>
                <Text style={styles.name}>🏬 {s.store_nomi}</Text>
                <Text style={styles.summa}>{money(s.summa)} som</Text>
                <Text style={styles.muted}>💳 {s.karta_raqami}</Text>
                <Btn label="✅ To'landi deb belgilash" tone="gold" disabled={busy} style={{ marginTop: 10 }}
                  onPress={() => act(`/api/moliya/withdraws/${s.id}/paid`, undefined, "To'landi deb belgilandi")} />
              </Card>
            )))}

          {tab === "refunds" && (rows.length === 0 ? <Empty text="Yangi so'rov yo'q." /> :
            rows.map((s) => (
              <Card key={s.id}>
                <Text style={styles.name}>{s.ism || `ID ${s.telegram_id}`}</Text>
                <Text style={styles.summa}>{money(s.summa)} som</Text>
                <Text style={styles.muted}>💳 {s.karta_raqami}</Text>
                <View style={styles.actions}>
                  <Btn label="✅ Tasdiqlash" tone="store" disabled={busy} style={{ flex: 1 }}
                    onPress={() => act(`/api/moliya/refunds/${s.id}/approve`, undefined, "Qaytarish tasdiqlandi")} />
                  <Btn label="❌ Rad" tone="sale" disabled={busy} style={{ flex: 1 }}
                    onPress={() => reject(`/api/moliya/refunds/${s.id}/reject`)} />
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
  name: { fontWeight: "700", color: colors.text, fontSize: 15 },
  summa: { fontSize: 22, fontWeight: "800", color: colors.brand, marginTop: 2 },
  ai: { color: colors.store, fontWeight: "600", marginTop: 4 },
  muted: { color: colors.textMuted, fontSize: 13, marginTop: 4 },
  actions: { flexDirection: "row", gap: 8, marginTop: 12 },
});
