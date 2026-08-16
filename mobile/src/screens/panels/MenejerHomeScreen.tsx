/**
 * Menejer paneli (4.3) — do'kon so'rovlari, do'konlar + arenda, hisobot.
 * Faqat menejer roli.
 */
import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, Alert } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { api, money } from "../../api";
import { colors, radius, spacing, font } from "../../theme";
import { Screen, Segmented, Card, Btn, Loader, Empty, Field } from "./PanelUI";

const TABS = [
  { key: "sorovlar", label: "🏪 Do'kon so'rovlari" },
  { key: "dokonlar", label: "📦 Do'konlar / Arenda" },
  { key: "report", label: "📊 Hisobot" },
];

export default function MenejerHomeScreen() {
  const [tab, setTab] = useState("sorovlar");
  const [rows, setRows] = useState<any[]>([]);
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
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

  async function act(path: string, body?: any) {
    const { ok, data } = await api(path, { method: "POST", body });
    if (ok) load();
    else Alert.alert("Xatolik", (data as any)?.detail || "Amal bajarilmadi.");
  }

  function reject(path: string) {
    const doIt = (sabab: string) => act(path, { sabab });
    if (Alert.prompt) Alert.prompt("Rad etish", "Sababini kiriting:", (s) => doIt(s?.trim() || ""));
    else doIt("");
  }

  function arendaColor(s: any) {
    if (s.holat === "bloklangan") return colors.sale;
    if (s.holat === "faol") return colors.store;
    return colors.textMuted;
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <Segmented items={TABS} value={tab} onChange={setTab} />
      {loading ? (
        <Loader />
      ) : (
        <Screen>
          {tab === "report" && report && (
            <Card style={{ backgroundColor: "rgba(201,151,26,0.10)", borderColor: "rgba(201,151,26,0.35)" }}>
              <Text style={styles.h}>💰 Platforma hisobida</Text>
              <Text style={styles.big}>{money(report.platforma_hisobida)} som</Text>
              <Field label="Mijozlar balansi" value={`${money(report.jami_mijozlar_balansi)} som`} />
              <Field label="Adminlar balansi" value={`${money(report.jami_adminlar_balansi)} som`} />
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
                  <Btn label="✅ Tasdiqlash" tone="store" style={{ flex: 1 }}
                    onPress={() => act(`/api/menejer/dokon-sorovlari/${s.id}/approve`)} />
                  <Btn label="❌ Rad" tone="sale" style={{ flex: 1 }}
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
                <View style={styles.actions}>
                  <Btn label="💵 Arenda uzaytirish" tone="gold" style={{ flex: 1 }}
                    onPress={() => act(`/api/menejer/stores/${s.id}/arenda-uzaytir`)} />
                  {s.holat === "bloklangan" ? (
                    <Btn label="🔓 Blokdan chiqar" tone="store" style={{ flex: 1 }}
                      onPress={() => act(`/api/menejer/stores/${s.id}/unblock`)} />
                  ) : (
                    <Btn label="🔒 Bloklash" tone="sale" style={{ flex: 1 }}
                      onPress={() => act(`/api/menejer/stores/${s.id}/block`)} />
                  )}
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
});
