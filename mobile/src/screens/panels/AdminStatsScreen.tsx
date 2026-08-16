/**
 * Admin — statistika + eng ko'p sotilgan + mahfiy kod (4.1).
 */
import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, Alert } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { api, money } from "../../api";
import { colors, radius, spacing, font } from "../../theme";
import { Screen, Loader, Card, Field, Btn } from "./PanelUI";

export default function AdminStatsScreen({ route }: any) {
  const { storeId } = route.params;
  const [stats, setStats] = useState<any>(null);
  const [top, setTop] = useState<any[]>([]);
  const [secret, setSecret] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const [s, t, c] = await Promise.all([
      api(`/api/admin/stores/${storeId}/stats`),
      api(`/api/admin/stores/${storeId}/top-products`),
      api(`/api/admin/stores/${storeId}/secret-code`),
    ]);
    if (s.ok) setStats(s.data);
    if (t.ok && Array.isArray(t.data)) setTop(t.data as any[]);
    if (c.ok) setSecret((c.data as any)?.mahfiy_kirish_kodi ?? null);
    setLoading(false);
  }, [storeId]);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  async function refreshSecret() {
    const { ok, data } = await api(`/api/admin/stores/${storeId}/secret-code/refresh`, { method: "POST" });
    if (ok) setSecret((data as any)?.mahfiy_kirish_kodi ?? null);
    else Alert.alert("Xatolik", "Kod yangilanmadi.");
  }

  if (loading) return <Loader />;

  return (
    <Screen>
      <Card>
        <Text style={styles.h}>📊 Umumiy</Text>
        <Field label="Buyurtmalar" value={String(stats?.umumiy_buyurtma ?? 0)} />
        <Field label="Tasdiqlangan" value={String(stats?.tasdiqlangan_buyurtma ?? 0)} />
        <Field label="Mahsulotlar" value={String(stats?.mahsulot_soni ?? 0)} />
        <View style={styles.tushum}>
          <Text style={styles.tushumLabel}>Umumiy tushum</Text>
          <Text style={styles.tushumVal}>{money(stats?.umumiy_tushum ?? 0)} som</Text>
        </View>
      </Card>

      <Card>
        <Text style={styles.h}>🔥 Eng ko'p sotilgan</Text>
        {top.length === 0 ? (
          <Text style={styles.muted}>Hali sotuv yo'q.</Text>
        ) : (
          top.map((p, i) => (
            <View key={i} style={styles.topRow}>
              <Text style={styles.topName}>{i + 1}. {p.nomi}</Text>
              <Text style={styles.topCnt}>{p.soni} dona</Text>
            </View>
          ))
        )}
      </Card>

      <Card>
        <Text style={styles.h}>🔒 Mahfiy kirish kodi</Text>
        <Text style={styles.secret}>{secret || "—"}</Text>
        <Text style={styles.muted}>Mijoz shu kod bilan mahfiy mahsulotlarни ochadi.</Text>
        <Btn label="🔄 Yangi kod yaratish" onPress={refreshSecret} tone="ghost" style={{ marginTop: 12 }} />
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  h: { fontSize: font.h2, fontWeight: "800", color: colors.text, marginBottom: 10 },
  muted: { color: colors.textMuted, fontSize: 13 },
  tushum: {
    marginTop: 12, borderTopWidth: 1, borderTopColor: colors.line, paddingTop: 12,
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
  },
  tushumLabel: { color: colors.textMuted },
  tushumVal: { fontSize: 20, fontWeight: "800", color: colors.gold },
  topRow: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 5 },
  topName: { color: colors.text, fontWeight: "600" },
  topCnt: { color: colors.store, fontWeight: "700" },
  secret: { fontSize: 32, fontWeight: "900", letterSpacing: 6, color: colors.brand, textAlign: "center", paddingVertical: 8 },
});
