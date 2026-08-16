/**
 * Admin — mahsulotlar ro'yxati (4.1): qo'shish / tahrirlash / o'chirish.
 */
import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, FlatList, TouchableOpacity, Alert } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { Ionicons } from "@expo/vector-icons";
import { api, money } from "../../api";
import { colors, radius, spacing } from "../../theme";
import { Loader, Empty } from "./PanelUI";

export default function AdminProductsScreen({ route, navigation }: any) {
  const { storeId, storeNomi } = route.params;
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const { ok, data } = await api<any[]>(`/api/admin/stores/${storeId}/products`);
    setRows(ok && Array.isArray(data) ? data : []);
    setLoading(false);
  }, [storeId]);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  function remove(p: any) {
    Alert.alert("O'chirish", `"${p.nomi}" mahsulotini o'chirasizmi?`, [
      { text: "Yo'q" },
      {
        text: "Ha, o'chir",
        style: "destructive",
        onPress: async () => {
          const { ok } = await api(`/api/admin/products/${p.id}`, { method: "DELETE" });
          if (ok) load();
          else Alert.alert("Xatolik", "O'chirilmadi.");
        },
      },
    ]);
  }

  if (loading) return <Loader />;

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <FlatList
        contentContainerStyle={{ padding: spacing.lg, paddingBottom: 90 }}
        data={rows}
        keyExtractor={(p) => String(p.id)}
        ListEmptyComponent={<Empty text="Mahsulot yo'q. Pastdan qo'shing." />}
        renderItem={({ item: p }) => (
          <View style={styles.row}>
            <View style={{ flex: 1 }}>
              <Text style={styles.name}>{p.nomi}</Text>
              <Text style={styles.price}>
                {money(p.narxi)} som
                {p.skidka_foizi ? <Text style={styles.sale}>  −{p.skidka_foizi}%</Text> : null}
              </Text>
              <Text style={styles.meta}>
                {p.korinish === "mahfiy" ? "🔒 Mahfiy" : "🌍 Ommaviy"}
                {p.miqdor != null ? `  ·  ${p.miqdor} dona` : ""}
              </Text>
            </View>
            <TouchableOpacity
              style={styles.iconBtn}
              onPress={() => navigation.navigate("AdminProductEdit", { storeId, product: p })}
            >
              <Ionicons name="create-outline" size={22} color={colors.brand} />
            </TouchableOpacity>
            <TouchableOpacity style={styles.iconBtn} onPress={() => remove(p)}>
              <Ionicons name="trash-outline" size={22} color={colors.sale} />
            </TouchableOpacity>
          </View>
        )}
      />
      <TouchableOpacity
        style={styles.fab}
        onPress={() => navigation.navigate("AdminProductEdit", { storeId })}
      >
        <Ionicons name="add" size={24} color="#fff" />
        <Text style={styles.fabText}>Yangi mahsulot</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row", alignItems: "center", gap: 6,
    borderBottomWidth: 1, borderBottomColor: colors.line, paddingVertical: 12,
  },
  name: { fontWeight: "700", color: colors.text, fontSize: 15 },
  price: { color: colors.store, marginTop: 2, fontWeight: "600" },
  sale: { color: colors.sale, fontWeight: "800" },
  meta: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
  iconBtn: { padding: 8 },
  fab: {
    position: "absolute", bottom: 20, alignSelf: "center", flexDirection: "row",
    alignItems: "center", gap: 6, backgroundColor: colors.brand,
    paddingVertical: 13, paddingHorizontal: 22, borderRadius: 999,
  },
  fabText: { color: "#fff", fontWeight: "800" },
});
