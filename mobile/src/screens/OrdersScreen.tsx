import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, FlatList, RefreshControl } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { api, money } from "../api";
import { colors, radius, spacing, font } from "../theme";
import { Order } from "../types";
import { Loader } from "./panels/PanelUI";

const HOLAT: Record<string, { t: string; c: string }> = {
  yangi: { t: "🆕 Yangi", c: "#1976d2" },
  tayyorlanmoqda: { t: "👨‍🍳 Tayyorlanmoqda", c: "#e65100" },
  yolda: { t: "🚚 Yo'lda", c: colors.brand },
  topshirildi: { t: "✅ Topshirildi", c: colors.store },
  bekor_qilindi: { t: "❌ Bekor qilindi", c: "#c62828" },
};

export default function OrdersScreen() {
  const [rows, setRows] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const { ok, data } = await api<Order[]>("/api/orders");
    setRows(ok && Array.isArray(data) ? data : []);
    setLoading(false);
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  if (loading) return <Loader />;

  return (
    <FlatList
      style={{ backgroundColor: colors.bg }}
      contentContainerStyle={{ padding: spacing.lg }}
      data={rows}
      keyExtractor={(o) => String(o.id)}
      refreshControl={<RefreshControl refreshing={false} onRefresh={load} />}
      ListEmptyComponent={<Text style={styles.empty}>Buyurtmalar yo'q.</Text>}
      renderItem={({ item: o }) => {
        const st = HOLAT[o.holat] || { t: o.holat, c: colors.textMuted };
        return (
          <View style={styles.card}>
            <View style={styles.head}>
              <Text style={styles.label}>Buyurtma kodi</Text>
              <Text style={[styles.badge, { color: st.c }]}>{st.t}</Text>
            </View>
            <Text style={styles.code}>{o.kod}</Text>
            {!!o.kuryer_tel && <Text style={styles.kuryer}>🚚 Kuryer: {o.kuryer_tel}</Text>}
            <View style={styles.totalRow}>
              <Text>Jami</Text>
              <Text style={styles.total}>{money(o.jami_narx)} som</Text>
            </View>
          </View>
        );
      }}
    />
  );
}

const styles = StyleSheet.create({
  empty: { textAlign: "center", color: colors.textMuted, marginTop: 40 },
  card: { backgroundColor: colors.cardTop, borderWidth: 1, borderColor: colors.line, borderRadius: radius.lg, padding: 16, marginBottom: 12 },
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  label: { fontSize: 12, color: colors.textMuted, textTransform: "uppercase" },
  badge: { fontWeight: "700", fontSize: 12 },
  code: { fontSize: 30, fontWeight: "800", letterSpacing: 4, color: colors.brand, textAlign: "center", paddingVertical: 10 },
  kuryer: { color: colors.store, fontWeight: "600", marginBottom: 6 },
  totalRow: { flexDirection: "row", justifyContent: "space-between", borderTopWidth: 1, borderTopColor: colors.line, paddingTop: 8 },
  total: { fontWeight: "800", color: colors.gold },
});
