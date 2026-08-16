/**
 * Admin — buyurtmalar (4.1): holatni o'zgartirish, qabul qilish, bekor qilish.
 */
import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, FlatList, RefreshControl, Alert } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { api, money } from "../../api";
import { colors, radius, spacing } from "../../theme";
import { Loader, Empty, Btn } from "./PanelUI";

const HOLAT: Record<string, { t: string; c: string }> = {
  yangi: { t: "🆕 Yangi", c: "#1976d2" },
  tayyorlanmoqda: { t: "👨‍🍳 Tayyorlanmoqda", c: "#e65100" },
  yolda: { t: "🚚 Yo'lda", c: colors.brand },
  topshirildi: { t: "✅ Topshirildi", c: colors.store },
  bekor_qilindi: { t: "❌ Bekor qilindi", c: "#c62828" },
};
const NEXT: Record<string, { holat: string; label: string }> = {
  yangi: { holat: "tayyorlanmoqda", label: "▶ Tayyorlashга" },
  tayyorlanmoqda: { holat: "yolda", label: "🚚 Yo'lга chiqarish" },
  yolda: { holat: "topshirildi", label: "✅ Topshirildi" },
};

export default function AdminOrdersScreen({ route }: any) {
  const { storeId } = route.params;
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const { ok, data } = await api<any[]>(`/api/admin/stores/${storeId}/orders`);
    setRows(ok && Array.isArray(data) ? data : []);
    setLoading(false);
  }, [storeId]);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  async function setStatus(o: any, holat: string, kuryer_tel?: string) {
    const { ok, data } = await api(`/api/admin/orders/${o.id}/status`, {
      method: "PATCH", body: { holat, kuryer_tel: kuryer_tel || null },
    });
    if (ok) load();
    else Alert.alert("Xatolik", (data as any)?.detail || "O'zgartirilmadi.");
  }

  function advance(o: any) {
    const nx = NEXT[o.holat];
    if (!nx) return;
    if (nx.holat === "yolda") {
      if (Alert.prompt) {
        Alert.prompt("Kuryer telefoni", "Kuryer raqamini kiriting (ixtiyoriy):",
          (tel) => setStatus(o, "yolda", tel?.trim() || undefined));
      } else {
        setStatus(o, "yolda");
      }
    } else {
      setStatus(o, nx.holat);
    }
  }

  function cancel(o: any) {
    const doCancel = (sabab: string) =>
      api(`/api/admin/orders/${o.id}/cancel`, { method: "POST", body: { sabab } }).then((r) =>
        r.ok ? load() : Alert.alert("Xatolik", (r.data as any)?.detail || "Bekor qilinmadi.")
      );
    if (Alert.prompt) {
      Alert.prompt("Bekor qilish", "Sababini kiriting:", (s) => s?.trim() && doCancel(s.trim()));
    } else {
      doCancel("Admin bekor qildi");
    }
  }

  if (loading) return <Loader />;

  return (
    <FlatList
      style={{ backgroundColor: colors.bg }}
      contentContainerStyle={{ padding: spacing.lg }}
      data={rows}
      keyExtractor={(o) => String(o.id)}
      refreshControl={<RefreshControl refreshing={false} onRefresh={load} />}
      ListEmptyComponent={<Empty text="Buyurtmalar yo'q." />}
      renderItem={({ item: o }) => {
        const st = HOLAT[o.holat] || { t: o.holat, c: colors.textMuted };
        const nx = NEXT[o.holat];
        const active = o.holat !== "topshirildi" && o.holat !== "bekor_qilindi";
        return (
          <View style={styles.card}>
            <View style={styles.head}>
              <Text style={styles.code}>{o.kod}</Text>
              <Text style={[styles.badge, { color: st.c }]}>{st.t}</Text>
            </View>
            {(o.mahsulotlar || []).map((m: any, i: number) => (
              <Text key={i} style={styles.item}>• {m.nomi} × {m.soni}</Text>
            ))}
            {!!o.manzil && <Text style={styles.meta}>📍 {o.manzil}</Text>}
            <View style={styles.totalRow}>
              <Text>Jami</Text>
              <Text style={styles.total}>{money(o.jami_narx)} som</Text>
            </View>
            {active && (
              <View style={styles.actions}>
                {nx && <Btn label={nx.label} onPress={() => advance(o)} tone="store" style={{ flex: 1 }} />}
                <Btn label="Bekor" onPress={() => cancel(o)} tone="sale" style={{ flex: 1 }} />
              </View>
            )}
          </View>
        );
      }}
    />
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.cardTop, borderWidth: 1, borderColor: colors.line,
    borderRadius: radius.lg, padding: 14, marginBottom: 12,
  },
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  code: { fontSize: 20, fontWeight: "800", letterSpacing: 2, color: colors.brand },
  badge: { fontWeight: "700", fontSize: 12 },
  item: { color: colors.text, marginTop: 6 },
  meta: { color: colors.textMuted, fontSize: 12, marginTop: 6 },
  totalRow: {
    flexDirection: "row", justifyContent: "space-between",
    borderTopWidth: 1, borderTopColor: colors.line, paddingTop: 8, marginTop: 8,
  },
  total: { fontWeight: "800", color: colors.gold },
  actions: { flexDirection: "row", gap: 8, marginTop: 12 },
});
