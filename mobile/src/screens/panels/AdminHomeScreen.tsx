/**
 * Admin paneli — do'kon tanlash + vositalar (4.1).
 * Do'kon admini o'z do'koni(lari)ni boshqaradi: mahsulot, buyurtma, statistika,
 * pul yechish, mahfiy kod.
 */
import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { Ionicons } from "@expo/vector-icons";
import { api } from "../../api";
import { colors, radius, spacing, font } from "../../theme";
import { Screen, Loader, Empty } from "./PanelUI";

type Store = { id: number; nomi: string; holat: string; kutilayotgan_balans: number };

const TOOLS: {
  key: string;
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  screen: string;
}[] = [
  { key: "p", label: "Mahsulotlar", icon: "cube-outline", screen: "AdminProducts" },
  { key: "o", label: "Buyurtmalar", icon: "receipt-outline", screen: "AdminOrders" },
  { key: "s", label: "Statistika", icon: "stats-chart-outline", screen: "AdminStats" },
  { key: "w", label: "Pul yechish", icon: "wallet-outline", screen: "AdminWithdraw" },
];

export default function AdminHomeScreen({ navigation }: any) {
  const [stores, setStores] = useState<Store[]>([]);
  const [sel, setSel] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const { ok, data } = await api<Store[]>("/api/admin/my-stores");
    const list = ok && Array.isArray(data) ? data : [];
    setStores(list);
    setSel((cur) => cur ?? (list[0]?.id ?? null));
    setLoading(false);
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  if (loading) return <Loader />;
  if (!stores.length)
    return <Empty text="Sizga biriktirilgan do'kon yo'q." />;

  const store = stores.find((s) => s.id === sel) || stores[0];

  return (
    <Screen>
      {stores.length > 1 && (
        <View style={styles.picker}>
          {stores.map((s) => (
            <TouchableOpacity
              key={s.id}
              onPress={() => setSel(s.id)}
              style={[styles.pill, s.id === sel && styles.pillActive]}
            >
              <Text style={[styles.pillText, s.id === sel && styles.pillTextActive]}>
                {s.nomi}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      <View style={styles.hero}>
        <Text style={styles.storeName}>🏬 {store.nomi}</Text>
        <Text style={styles.holat}>Holat: {store.holat}</Text>
        <Text style={styles.balLabel}>Kutilayotgan balans</Text>
        <Text style={styles.bal}>{store.kutilayotgan_balans.toLocaleString("en-US")} som</Text>
      </View>

      <View style={styles.grid}>
        {TOOLS.map((t) => (
          <TouchableOpacity
            key={t.key}
            style={styles.tool}
            onPress={() =>
              navigation.navigate(t.screen, { storeId: store.id, storeNomi: store.nomi })
            }
          >
            <Ionicons name={t.icon} size={26} color={colors.brand} />
            <Text style={styles.toolText}>{t.label}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  picker: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: spacing.md },
  pill: {
    paddingVertical: 8, paddingHorizontal: 14, borderRadius: 999,
    backgroundColor: colors.secondaryBg,
  },
  pillActive: { backgroundColor: colors.store },
  pillText: { color: colors.textMuted, fontWeight: "700" },
  pillTextActive: { color: "#fff" },
  hero: {
    backgroundColor: colors.cardTop, borderWidth: 1, borderColor: colors.line,
    borderRadius: radius.lg, padding: spacing.xl, marginBottom: spacing.lg,
  },
  storeName: { fontSize: font.h1, fontWeight: "800", color: colors.store },
  holat: { color: colors.textMuted, marginTop: 2 },
  balLabel: { color: colors.textMuted, marginTop: 14, fontSize: 12 },
  bal: { fontSize: 26, fontWeight: "800", color: colors.gold },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  tool: {
    width: "47%", flexGrow: 1, backgroundColor: colors.bg, borderWidth: 1,
    borderColor: colors.line, borderRadius: radius.lg, paddingVertical: 22,
    alignItems: "center", gap: 8,
  },
  toolText: { fontWeight: "700", color: colors.text },
});
