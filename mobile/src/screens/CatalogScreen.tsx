/**
 * Katalog — ilovaning yuzi.
 *
 * 2026 mobil savdo me'yorlari asosida:
 *   • Do'kon bo'yicha filtr chiplari (marketplace odati — Uzum/Ozon/WB).
 *   • Skeleton yuklash (spinner emas) — ekran "sakramaydi".
 *   • Bosishga spring javobi, yumshoq ko'p qatlamli soya, yirik radius.
 *   • Narx ierarxiyasi: yakuniy narx yirik, eski narx ustidan chizilgan.
 *   • Toast — Alert emas (ekranni to'smaydi).
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  View, Text, StyleSheet, FlatList, TextInput, Image, TouchableOpacity,
  RefreshControl, Animated, ScrollView,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { api, money } from "../api";
import { colors, radius, spacing, font, shadow, tracking , border } from "../theme";
import { SkeletonCatalog } from "../ui/Skeleton";
import { Press } from "../ui/Press";
import { Product, effPrice, rasmUrl } from "../types";
import { ChegirmaTaymer } from "../ui/Glass";
import { useCart } from "../cart/CartContext";

const HAMMASI = "__hammasi__";

/** 2 ustunli to'r uchun ro'yxatni juftlaydi (yolg'iz kartochka cho'zilmasin). */
function juftla(list: Product[]): (Product | null)[] {
  return list.length % 2 === 1 ? [...list, null] : list;
}

export default function CatalogScreen({ navigation }: any) {
  const { add, count } = useCart();
  const [all, setAll] = useState<Product[]>([]);
  const [q, setQ] = useState("");
  const [dokon, setDokon] = useState<string>(HAMMASI);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    const { ok, data } = await api<Product[]>("/api/products");
    setAll(ok && Array.isArray(data) ? data : []);
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  // Do'konlar ro'yxati — filtr chiplari uchun.
  const dokonlar = useMemo(() => {
    const s = new Set<string>();
    all.forEach((p) => p.store_nomi && s.add(p.store_nomi));
    return Array.from(s);
  }, [all]);

  const list = all.filter((p) => {
    const nomMos = !q || p.nomi.toLowerCase().includes(q.toLowerCase());
    const dokonMos = dokon === HAMMASI || p.store_nomi === dokon;
    return nomMos && dokonMos;
  });

  function qoshildi(p: Product) {
    add(p, null, null);
    setToast(`${p.nomi} — savatga qo'shildi`);
  }

  function Card({ p }: { p: Product }) {
    const img = rasmUrl(p);
    const sotuv = effPrice(p);
    const chegirma = !!p.skidka_foizi && p.skidka_foizi > 0;
    return (
      <Press
        style={styles.card}
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
              <View style={styles.tugadiPill}>
                <Text style={styles.tugadiText}>Tugadi</Text>
              </View>
            </View>
          )}
          {/* Chegirma taymeri — rasm ustida, shisha yuzada */}
          {chegirma && !!p.skidka_muddati && !p.tugadi && (
            <View style={styles.taymerJoy}>
              <ChegirmaTaymer muddat={p.skidka_muddati} kichik />
            </View>
          )}
          {/* Bir nechta rasm borligi belgisi */}
          {(p.rasm_urls?.length || 0) > 1 && (
            <View style={styles.kopRasm}>
              <Ionicons name="images-outline" size={11} color="#fff" />
              <Text style={styles.kopRasmText}>{p.rasm_urls!.length}</Text>
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
          {sotuv < p.narxi ? (
            <Text style={styles.old}>{money(p.narxi)} som</Text>
          ) : (
            <View style={{ height: 15 }} />
          )}

          <TouchableOpacity
            style={[styles.addBtn, p.tugadi && styles.disabled]}
            disabled={!!p.tugadi}
            activeOpacity={0.85}
            onPress={() =>
              p.olcham || p.rang
                ? navigation.navigate("Product", { product: p })
                : qoshildi(p)
            }
          >
            <Ionicons name="bag-add-outline" size={16} color="#fff" />
            <Text style={styles.addText}>Savatga</Text>
          </TouchableOpacity>
        </View>
      </Press>
    );
  }

  return (
    <View style={styles.container}>
      {/* Sarlavha */}
      <View style={styles.header}>
        <View style={styles.brend}>
          <Image source={require("../../assets/icon.png")} style={styles.brendLogo} />
          <View>
            <Text style={styles.logo}>ARZON</Text>
            <Text style={styles.shior}>Onlayn savdo</Text>
          </View>
        </View>
        <Press scale={0.9} onPress={() => navigation.navigate("Savat")}>
          <View style={styles.cartBtn}>
            <Ionicons name="bag-outline" size={22} color={colors.brand} />
            {count > 0 && (
              <View style={styles.badge}>
                <Text style={styles.badgeText}>{count}</Text>
              </View>
            )}
          </View>
        </Press>
      </View>

      {/* Qidiruv */}
      <View style={styles.searchWrap}>
        <Ionicons name="search" size={18} color={colors.textFaint} />
        <TextInput
          style={styles.search}
          placeholder="Mahsulot qidirish"
          placeholderTextColor={colors.textFaint}
          value={q}
          onChangeText={setQ}
          returnKeyType="search"
        />
        {!!q && (
          <TouchableOpacity onPress={() => setQ("")} hitSlop={8}>
            <Ionicons name="close-circle" size={18} color={colors.textFaint} />
          </TouchableOpacity>
        )}
      </View>

      {/* Do'kon chiplari */}
      {dokonlar.length > 1 && (
        <View style={styles.chipHost}>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.chipWrap}
          >
            {[HAMMASI, ...dokonlar].map((d) => {
              const faol = d === dokon;
              return (
                <TouchableOpacity
                  key={d}
                  onPress={() => setDokon(d)}
                  activeOpacity={0.8}
                  style={[styles.chip, faol && styles.chipOn]}
                >
                  <Text style={[styles.chipText, faol && styles.chipTextOn]}>
                    {d === HAMMASI ? "Hammasi" : d}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </ScrollView>
        </View>
      )}

      {loading ? (
        <SkeletonCatalog soni={6} />
      ) : (
        <FlatList
          data={juftla(list)}
          keyExtractor={(p, i) => (p ? String(p.id) : `bosh-${i}`)}
          numColumns={2}
          columnWrapperStyle={styles.qator}
          contentContainerStyle={styles.royxat}
          showsVerticalScrollIndicator={false}
          renderItem={({ item }) =>
            item ? <Card p={item} /> : <View style={{ flex: 1 }} />
          }
          refreshControl={
            <RefreshControl refreshing={false} onRefresh={load} tintColor={colors.brand} />
          }
          ListEmptyComponent={
            <View style={styles.empty}>
              <View style={styles.emptyIcon}>
                <Ionicons
                  name={q ? "search-outline" : "bag-handle-outline"}
                  size={34}
                  color={colors.textFaint}
                />
              </View>
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
  const y = useRef(new Animated.Value(90)).current;
  useEffect(() => {
    if (!text) return;
    Animated.spring(y, { toValue: 0, useNativeDriver: true, friction: 9 }).start();
    const t = setTimeout(() => {
      Animated.timing(y, { toValue: 90, duration: 180, useNativeDriver: true })
        .start(() => onHide());
    }, 1500);
    return () => clearTimeout(t);
  }, [text]);
  if (!text) return null;
  return (
    <Animated.View style={[styles.toast, { transform: [{ translateY: y }] }]}>
      <Ionicons name="checkmark-circle" size={18} color="#4ADE80" />
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
  brendLogo: { width: 36, height: 36, borderRadius: radius.xs },
  logo: {
    fontSize: font.h1, fontWeight: "900", color: colors.brand,
    letterSpacing: tracking.wide,
  },
  shior: { fontSize: font.tiny, color: colors.textFaint, marginTop: -3 },
  cartBtn: {
    width: 44, height: 44, borderRadius: radius.sm, alignItems: "center",
    justifyContent: "center", backgroundColor: colors.brandSoft,
  },
  badge: {
    position: "absolute", top: 1, right: 1, minWidth: 19, height: 19,
    borderRadius: 10, backgroundColor: colors.sale, alignItems: "center",
    justifyContent: "center", paddingHorizontal: 5,
    borderWidth: 2, borderColor: colors.bg,
  },
  badgeText: { color: "#fff", fontSize: 10, fontWeight: "800" },

  searchWrap: {
    flexDirection: "row", alignItems: "center", gap: 10,
    marginHorizontal: spacing.lg, marginTop: spacing.sm,
    backgroundColor: colors.bg, borderRadius: radius.pill,
    paddingHorizontal: 16, height: 46, ...border.hair,
  },
  search: { flex: 1, color: colors.text, fontSize: font.body, padding: 0 },

  chipHost: { height: 52, flexGrow: 0, flexShrink: 0 },
  chipWrap: {
    paddingHorizontal: spacing.lg, paddingVertical: spacing.md,
    gap: 8, alignItems: "center",
  },
  chip: {
    height: 34, justifyContent: "center", paddingHorizontal: 14,
    borderRadius: radius.pill, backgroundColor: colors.bg, ...border.hair,
  },
  chipOn: { backgroundColor: colors.text },
  chipText: { color: colors.textMuted, fontWeight: "700", fontSize: font.small },
  chipTextOn: { color: "#fff" },

  qator: { gap: spacing.md, paddingHorizontal: spacing.lg },
  royxat: { gap: spacing.md, paddingTop: spacing.md, paddingBottom: spacing.xxl },

  card: {
    flex: 1, backgroundColor: colors.bg, borderRadius: radius.lg,
    overflow: "hidden", ...border.hair,
  },
  imgWrap: {
    position: "relative", aspectRatio: 1, backgroundColor: colors.secondaryBg,
    alignItems: "center", justifyContent: "center",
  },
  img: { width: "100%", height: "100%" },
  noImg: { fontSize: 40, opacity: 0.5 },
  saleTag: {
    position: "absolute", left: 8, top: 8, backgroundColor: colors.sale,
    paddingHorizontal: 8, paddingVertical: 4, borderRadius: radius.xs,
  },
  saleText: { color: "#fff", fontSize: font.tiny, fontWeight: "900" },
  tugadiQoplama: {
    ...StyleSheet.absoluteFillObject, backgroundColor: "rgba(255,255,255,0.7)",
    alignItems: "center", justifyContent: "center",
  },
  tugadiPill: {
    backgroundColor: colors.text, paddingHorizontal: 14, paddingVertical: 6,
    borderRadius: radius.pill,
  },
  tugadiText: { fontWeight: "800", color: "#fff", fontSize: font.small },

  taymerJoy: { position: "absolute", left: 8, bottom: 8, right: 8 },
  kopRasm: {
    position: "absolute", right: 8, top: 8, flexDirection: "row",
    alignItems: "center", gap: 3, backgroundColor: "rgba(15,17,21,0.6)",
    paddingHorizontal: 7, paddingVertical: 3, borderRadius: radius.xs,
  },
  kopRasmText: { color: "#fff", fontSize: 10, fontWeight: "800" },
  info: { paddingHorizontal: 12, paddingTop: 10, paddingBottom: 12 },
  store: { fontSize: font.tiny, fontWeight: "700", color: colors.store, marginBottom: 3 },
  name: {
    fontWeight: "600", fontSize: font.small + 1, color: colors.text,
    lineHeight: 17, minHeight: 34,
  },
  priceRow: { flexDirection: "row", alignItems: "baseline", gap: 4, marginTop: 6 },
  priceB: {
    fontWeight: "900", fontSize: font.h2, color: colors.text,
    letterSpacing: tracking.h2,
  },
  som: { fontSize: font.tiny, color: colors.textMuted },
  old: {
    color: colors.textFaint, textDecorationLine: "line-through",
    fontSize: font.tiny, height: 15,
  },

  addBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6,
    marginTop: 10, backgroundColor: colors.brand,
    borderRadius: radius.sm, height: 38, borderWidth: 1, borderColor: colors.brand,
  },
  addText: { color: "#fff", fontWeight: "800", fontSize: font.small },
  disabled: { backgroundColor: colors.textFaint },

  empty: { alignItems: "center", marginTop: 70, gap: 10, paddingHorizontal: spacing.xl },
  emptyIcon: {
    width: 72, height: 72, borderRadius: 36, backgroundColor: colors.bg,
    alignItems: "center", justifyContent: "center", ...border.hair,
  },
  emptyTitle: {
    fontSize: font.h2, fontWeight: "800", color: colors.text,
    letterSpacing: tracking.h2, marginTop: 4,
  },
  emptyHint: { color: colors.textMuted, textAlign: "center", lineHeight: 20 },

  toast: {
    position: "absolute", left: spacing.lg, right: spacing.lg, bottom: spacing.lg,
    flexDirection: "row", alignItems: "center", gap: 10,
    backgroundColor: "rgba(15,17,21,0.95)", borderRadius: radius.md,
    paddingVertical: 14, paddingHorizontal: 16, ...shadow.lg,
  },
  toastText: { flex: 1, color: "#fff", fontWeight: "600", fontSize: font.body },
});
