import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  View, Text, StyleSheet, FlatList, TextInput, Image, TouchableOpacity,
  RefreshControl, Animated,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { api, money } from "../api";
import { colors, radius, spacing, font, shadow } from "../theme";
import { Loader } from "./panels/PanelUI";
import { Product, effPrice, rasmUrl } from "../types";
import { useCart } from "../cart/CartContext";

/** Ro'yxat elementlari sonini juft qiladi (2 ustunli to'r uchun).
 *  Toq bo'lsa oxiriga bo'sh o'rin (null) qo'shiladi — aks holda oxirgi
 *  kartochka butun kenglikka cho'zilib ketadi. */
function juftla(list: Product[]): (Product | null)[] {
  return list.length % 2 === 1 ? [...list, null] : list;
}

export default function CatalogScreen({ navigation }: any) {
  const { add, count } = useCart();
  const [all, setAll] = useState<Product[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    const { ok, data } = await api<Product[]>("/api/products");
    setAll(ok && Array.isArray(data) ? data : []);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const list = all.filter((p) => !q || p.nomi.toLowerCase().includes(q.toLowerCase()));

  function qoshildi(p: Product) {
    add(p, null, null);
    setToast(`✅ ${p.nomi} — savatga qo'shildi`);
  }

  function Card({ p }: { p: Product }) {
    const img = rasmUrl(p);
    const sotuv = effPrice(p);
    const chegirma = !!p.skidka_foizi && p.skidka_foizi > 0;
    return (
      <View style={styles.card}>
        <TouchableOpacity
          activeOpacity={0.85}
          onPress={() => navigation.navigate("Product", { product: p })}
        >
          <View style={styles.imgWrap}>
            {img ? (
              <Image source={{ uri: img }} style={styles.img} resizeMode="cover" />
            ) : (
              <Text style={styles.noImg}>🛍️</Text>
            )}
            {chegirma && (
              <View style={styles.saleTag}>
                <Text style={styles.saleText}>−{p.skidka_foizi}%</Text>
              </View>
            )}
            {!!p.tugadi && (
              <View style={styles.tugadiQoplama}>
                <Text style={styles.tugadiText}>Tugadi</Text>
              </View>
            )}
          </View>

          <View style={styles.info}>
            {!!p.store_nomi && (
              <Text style={styles.store} numberOfLines={1}>{p.store_nomi}</Text>
            )}
            <Text style={styles.name} numberOfLines={2}>{p.nomi}</Text>
            <View style={styles.priceRow}>
              <Text style={styles.priceB}>{money(sotuv)}</Text>
              <Text style={styles.som}>som</Text>
            </View>
            {sotuv < p.narxi && <Text style={styles.old}>{money(p.narxi)} som</Text>}
          </View>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.addBtn, p.tugadi && styles.disabled]}
          disabled={!!p.tugadi}
          activeOpacity={0.8}
          onPress={() =>
            p.olcham || p.rang
              ? navigation.navigate("Product", { product: p })
              : qoshildi(p)
          }
        >
          <Ionicons name="cart-outline" size={15} color="#fff" />
          <Text style={styles.addText}>Savatga</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Sarlavha — logotip va savat */}
      <View style={styles.header}>
        <View style={styles.brend}>
          <Image source={require("../../assets/icon.png")} style={styles.brendLogo} />
          <View>
            <Text style={styles.logo}>ARZON</Text>
            <Text style={styles.shior}>Onlayn savdo</Text>
          </View>
        </View>
        <TouchableOpacity style={styles.cartBtn} onPress={() => navigation.navigate("Savat")}>
          <Ionicons name="cart-outline" size={24} color={colors.brand} />
          {count > 0 && (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{count}</Text>
            </View>
          )}
        </TouchableOpacity>
      </View>

      {/* Qidiruv */}
      <View style={styles.searchWrap}>
        <Ionicons name="search" size={18} color={colors.textFaint} />
        <TextInput
          style={styles.search}
          placeholder="Mahsulot qidirish..."
          placeholderTextColor={colors.textFaint}
          value={q}
          onChangeText={setQ}
          returnKeyType="search"
        />
        {!!q && (
          <TouchableOpacity onPress={() => setQ("")}>
            <Ionicons name="close-circle" size={18} color={colors.textFaint} />
          </TouchableOpacity>
        )}
      </View>

      {loading ? (
        <Loader />
      ) : (
        <FlatList
          data={juftla(list)}
          keyExtractor={(p, i) => (p ? String(p.id) : `bosh-${i}`)}
          numColumns={2}
          columnWrapperStyle={styles.qator}
          contentContainerStyle={styles.royxat}
          // Bo'sh o'rin (null) — oxirgi qatorda yolg'iz qolgan kartochka butun
          // kenglikka cho'zilib ketmasligi uchun.
          renderItem={({ item }) =>
            item ? <Card p={item} /> : <View style={{ flex: 1 }} />
          }
          refreshControl={
            <RefreshControl refreshing={false} onRefresh={load} tintColor={colors.brand} />
          }
          ListEmptyComponent={
            <View style={styles.empty}>
              <Text style={{ fontSize: 46 }}>{q ? "🔍" : "🛍️"}</Text>
              <Text style={styles.emptyTitle}>
                {q ? "Hech narsa topilmadi" : "Hozircha mahsulot yo'q"}
              </Text>
              <Text style={styles.emptyHint}>
                {q ? "Boshqa so'z bilan qidirib ko'ring." : "Tez orada qo'shiladi."}
              </Text>
            </View>
          }
        />
      )}

      <Toast text={toast} onHide={() => setToast(null)} />
    </View>
  );
}

/** Yengil bildirishnoma — Alert kabi ekranni to'smaydi. */
function Toast({ text, onHide }: { text: string | null; onHide: () => void }) {
  const y = useRef(new Animated.Value(80)).current;
  useEffect(() => {
    if (!text) return;
    Animated.spring(y, { toValue: 0, useNativeDriver: true, friction: 8 }).start();
    const t = setTimeout(() => {
      Animated.timing(y, { toValue: 80, duration: 180, useNativeDriver: true })
        .start(() => onHide());
    }, 1400);
    return () => clearTimeout(t);
  }, [text]);
  if (!text) return null;
  return (
    <Animated.View style={[styles.toast, { transform: [{ translateY: y }] }]}>
      <Text style={styles.toastText} numberOfLines={2}>{text}</Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bgSoft },

  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: spacing.lg, paddingTop: spacing.md, paddingBottom: spacing.sm,
    backgroundColor: colors.bg,
  },
  brend: { flexDirection: "row", alignItems: "center", gap: 10 },
  brendLogo: { width: 38, height: 38, borderRadius: radius.sm },
  logo: { fontSize: font.h1, fontWeight: "900", color: colors.brand, letterSpacing: 1.5 },
  shior: { fontSize: font.tiny, color: colors.textFaint, letterSpacing: 0.5, marginTop: -2 },
  cartBtn: {
    width: 44, height: 44, borderRadius: radius.md, alignItems: "center",
    justifyContent: "center", backgroundColor: colors.brandSoft,
  },
  badge: {
    position: "absolute", top: 2, right: 2, minWidth: 18, height: 18,
    borderRadius: 9, backgroundColor: colors.sale, alignItems: "center",
    justifyContent: "center", paddingHorizontal: 4,
  },
  badgeText: { color: "#fff", fontSize: 10, fontWeight: "800" },

  searchWrap: {
    flexDirection: "row", alignItems: "center", gap: 8,
    marginHorizontal: spacing.lg, marginTop: spacing.sm, marginBottom: spacing.md,
    backgroundColor: colors.bg, borderRadius: radius.pill,
    paddingHorizontal: 14, height: 44, ...shadow.sm,
  },
  search: { flex: 1, color: colors.text, fontSize: font.body, padding: 0 },

  qator: { gap: spacing.md, paddingHorizontal: spacing.lg },
  royxat: { gap: spacing.md, paddingBottom: spacing.xxl },

  card: {
    flex: 1, backgroundColor: colors.bg, borderRadius: radius.lg,
    overflow: "hidden", ...shadow.sm,
  },
  imgWrap: {
    position: "relative", aspectRatio: 1, backgroundColor: colors.secondaryBg,
    alignItems: "center", justifyContent: "center",
  },
  img: { width: "100%", height: "100%" },
  noImg: { fontSize: 40 },
  saleTag: {
    position: "absolute", left: 8, top: 8, backgroundColor: colors.sale,
    paddingHorizontal: 8, paddingVertical: 3, borderRadius: radius.xs,
  },
  saleText: { color: "#fff", fontSize: font.tiny, fontWeight: "900" },
  tugadiQoplama: {
    ...StyleSheet.absoluteFillObject, backgroundColor: "rgba(255,255,255,0.72)",
    alignItems: "center", justifyContent: "center",
  },
  tugadiText: { fontWeight: "800", color: colors.textMuted, fontSize: font.h3 },

  info: { paddingHorizontal: 10, paddingTop: 8 },
  store: { fontSize: font.tiny, fontWeight: "700", color: colors.store, marginBottom: 2 },
  name: { fontWeight: "600", fontSize: font.small + 1, color: colors.text, lineHeight: 17, minHeight: 34 },
  priceRow: { flexDirection: "row", alignItems: "baseline", gap: 3, marginTop: 4 },
  priceB: { fontWeight: "900", fontSize: font.h3, color: colors.text },
  som: { fontSize: font.tiny, color: colors.textMuted },
  old: { color: colors.textFaint, textDecorationLine: "line-through", fontSize: font.tiny },

  addBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 5,
    margin: 10, marginTop: 8, backgroundColor: colors.brand,
    borderRadius: radius.sm, paddingVertical: 9,
  },
  addText: { color: "#fff", fontWeight: "800", fontSize: font.small },
  disabled: { backgroundColor: colors.textFaint },

  empty: { alignItems: "center", marginTop: 60, gap: 8, paddingHorizontal: spacing.xl },
  emptyTitle: { fontSize: font.h2, fontWeight: "800", color: colors.text },
  emptyHint: { color: colors.textMuted, textAlign: "center" },

  toast: {
    position: "absolute", left: spacing.lg, right: spacing.lg, bottom: spacing.lg,
    backgroundColor: "rgba(20,20,20,0.93)", borderRadius: radius.md,
    paddingVertical: 12, paddingHorizontal: 16, ...shadow.lg,
  },
  toastText: { color: "#fff", fontWeight: "700", textAlign: "center" },
});
