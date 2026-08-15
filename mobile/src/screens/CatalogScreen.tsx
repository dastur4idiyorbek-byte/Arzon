import React, { useCallback, useEffect, useState } from "react";
import {
  View, Text, StyleSheet, FlatList, TextInput, Image, TouchableOpacity,
  ActivityIndicator, RefreshControl,
} from "react-native";
import { api, money } from "../api";
import { colors, radius, spacing, font } from "../theme";
import { Product, effPrice } from "../types";
import { useCart } from "../cart/CartContext";

export default function CatalogScreen({ navigation }: any) {
  const { add } = useCart();
  const [all, setAll] = useState<Product[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const { ok, data } = await api<Product[]>("/api/products");
    setAll(ok && Array.isArray(data) ? data : []);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const list = all.filter((p) => !q || p.nomi.toLowerCase().includes(q.toLowerCase()));

  function Card({ p }: { p: Product }) {
    const img = p.rasm_url || (p.rasm_urls && p.rasm_urls[0]);
    const sotuv = effPrice(p);
    return (
      <View style={styles.card}>
        <TouchableOpacity onPress={() => navigation.navigate("Product", { product: p })}>
          <View style={styles.imgWrap}>
            {img ? <Image source={{ uri: img }} style={styles.img} /> : <Text style={styles.noImg}>🛍️</Text>}
            {!!p.store_nomi && <Text style={styles.storeChip}>🏪 {p.store_nomi}</Text>}
            {!!p.skidka_foizi && p.skidka_foizi > 0 && <Text style={styles.sale}>-{p.skidka_foizi}%</Text>}
          </View>
          <Text style={styles.name} numberOfLines={2}>{p.nomi}</Text>
          <Text style={styles.price}>
            {sotuv < p.narxi && <Text style={styles.old}>{money(p.narxi)} </Text>}
            <Text style={styles.priceB}>{money(sotuv)}</Text> som
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.addBtn, p.tugadi && styles.disabled]}
          disabled={!!p.tugadi}
          onPress={() =>
            (p.olcham || p.rang)
              ? navigation.navigate("Product", { product: p })
              : add(p, null, null)
          }
        >
          <Text style={styles.addText}>{p.tugadi ? "Tugadi" : "🛒 Savatga"}</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.logo}>ARZON</Text>
      </View>
      <TextInput style={styles.search} placeholder="🔍 Mahsulot qidirish..." value={q} onChangeText={setQ} />
      {loading ? (
        <ActivityIndicator color={colors.brand} style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          data={list}
          keyExtractor={(p) => String(p.id)}
          numColumns={2}
          columnWrapperStyle={{ gap: spacing.md, paddingHorizontal: spacing.lg }}
          contentContainerStyle={{ gap: spacing.md, paddingBottom: 24 }}
          renderItem={({ item }) => <Card p={item} />}
          refreshControl={<RefreshControl refreshing={false} onRefresh={load} />}
          ListEmptyComponent={<Text style={styles.empty}>Hozircha mahsulot yo'q.</Text>}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  header: { paddingHorizontal: spacing.lg, paddingVertical: spacing.md, borderBottomWidth: 1, borderBottomColor: colors.line },
  logo: { fontSize: font.h1, fontWeight: "800", color: colors.brand, letterSpacing: 1 },
  search: {
    margin: spacing.lg, marginBottom: spacing.md, borderWidth: 1, borderColor: colors.line,
    backgroundColor: colors.secondaryBg, borderRadius: radius.sm, padding: 12,
  },
  card: { flex: 1, backgroundColor: colors.cardTop, borderWidth: 1, borderColor: colors.line, borderRadius: radius.md, padding: 8 },
  imgWrap: { position: "relative", aspectRatio: 1, backgroundColor: "#e6e6e6", borderRadius: radius.sm, alignItems: "center", justifyContent: "center", overflow: "hidden" },
  img: { width: "100%", height: "100%" },
  noImg: { fontSize: 40 },
  storeChip: { position: "absolute", left: 4, top: 4, fontSize: 10, fontWeight: "700", color: "#fff", backgroundColor: colors.store, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 8 },
  sale: { position: "absolute", right: 4, top: 4, fontSize: 10, fontWeight: "800", color: "#fff", backgroundColor: colors.sale, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 8 },
  name: { fontWeight: "700", fontSize: 13, marginTop: 6, color: colors.text },
  price: { marginTop: 4, fontSize: 13, color: colors.text },
  priceB: { fontWeight: "800" },
  old: { color: colors.textMuted, textDecorationLine: "line-through", fontSize: 11 },
  addBtn: { marginTop: 8, backgroundColor: colors.brand, borderRadius: radius.sm, paddingVertical: 9, alignItems: "center" },
  addText: { color: "#fff", fontWeight: "700", fontSize: 12 },
  disabled: { opacity: 0.4 },
  empty: { textAlign: "center", color: colors.textMuted, marginTop: 40 },
});
