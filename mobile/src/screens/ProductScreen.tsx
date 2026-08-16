import React, { useState, useRef, useEffect } from "react";
import { View, Text, StyleSheet, Image, ScrollView, TouchableOpacity, Alert, Animated } from "react-native";
import { money } from "../api";
import { colors, radius, spacing, font } from "../theme";
import { Product, effPrice, rasmUrl } from "../types";
import { useCart } from "../cart/CartContext";

const parse = (s?: string | null) => (s || "").split(",").map((x) => x.trim()).filter(Boolean);

export default function ProductScreen({ route, navigation }: any) {
  const p: Product = route.params.product;
  const { add } = useCart();
  const olchamlar = parse(p.olcham);
  const ranglar = parse(p.rang);
  const [olcham, setOlcham] = useState<string | null>(olchamlar.length === 1 ? olchamlar[0] : null);
  const [rang, setRang] = useState<string | null>(ranglar.length === 1 ? ranglar[0] : null);
  const [toast, setToast] = useState<string | null>(null);
  const img = rasmUrl(p);
  const sotuv = effPrice(p);

  /** Tanlovlar to'g'rimi? (o'lcham/rang majburiy bo'lsa) */
  function tanlovOk() {
    if (olchamlar.length && !olcham) {
      Alert.alert("O'lcham", "O'lchamni tanlang.");
      return false;
    }
    if (ranglar.length && !rang) {
      Alert.alert("Rang", "Rangni tanlang.");
      return false;
    }
    return true;
  }

  /** 🛒 Savatga qo'shish — ekranda qolamiz, qisqa bildirishnoma chiqadi. */
  function addToCart() {
    if (!tanlovOk()) return;
    add(p, olcham, rang);
    setToast("✅ Savatga qo'shildi");
  }

  /** ⚡ Sotib olish — savatga qo'shib, DARHOL savat (to'lov) ekraniga o'tamiz. */
  function buyNow() {
    if (!tanlovOk()) return;
    add(p, olcham, rang);
    navigation.navigate("Savat");
  }

  const Chips = ({ vals, sel, onSel }: { vals: string[]; sel: string | null; onSel: (v: string) => void }) => (
    <View style={styles.chips}>
      {vals.map((v) => (
        <TouchableOpacity key={v} onPress={() => onSel(v)} style={[styles.chip, sel === v && styles.chipOn]}>
          <Text style={[styles.chipText, sel === v && styles.chipTextOn]}>{v}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );

  return (
    <View style={styles.container}>
      <ScrollView>
        <View style={styles.imgWrap}>
          {img ? <Image source={{ uri: img }} style={styles.img} /> : <Text style={{ fontSize: 64 }}>🛍️</Text>}
        </View>
        <View style={styles.body}>
          {!!p.store_nomi && <Text style={styles.store}>🏪 {p.store_nomi}</Text>}
          <Text style={styles.name}>{p.nomi}</Text>
          <Text style={styles.price}>
            {sotuv < p.narxi && <Text style={styles.old}>{money(p.narxi)} </Text>}
            <Text style={styles.priceB}>{money(sotuv)}</Text> som
          </Text>
          {olchamlar.length > 0 && (<><Text style={styles.label}>O'lcham:</Text><Chips vals={olchamlar} sel={olcham} onSel={setOlcham} /></>)}
          {ranglar.length > 0 && (<><Text style={styles.label}>Rang:</Text><Chips vals={ranglar} sel={rang} onSel={setRang} /></>)}
          {!!p.tavsif && <Text style={styles.desc}>{p.tavsif}</Text>}
        </View>
      </ScrollView>
      {/* Ikki tugma: savatga qo'shish (ekranda qolamiz) va sotib olish (savatga o'tamiz) */}
      <View style={styles.bar}>
        {p.tugadi ? (
          <View style={[styles.buy, styles.disabled]}>
            <Text style={styles.buyText}>Tugadi</Text>
          </View>
        ) : (
          <>
            <TouchableOpacity style={[styles.cartBtn]} onPress={addToCart} activeOpacity={0.8}>
              <Text style={styles.cartText}>🛒 Savatga</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.buy]} onPress={buyNow} activeOpacity={0.8}>
              <Text style={styles.buyText}>Sotib olish</Text>
            </TouchableOpacity>
          </>
        )}
      </View>

      <Toast text={toast} onHide={() => setToast(null)} />
    </View>
  );
}

/** Yengil bildirishnoma — Alert kabi ekranni to'smaydi, o'zi yo'qoladi. */
function Toast({ text, onHide }: { text: string | null; onHide: () => void }) {
  const y = useRef(new Animated.Value(60)).current;
  useEffect(() => {
    if (!text) return;
    Animated.spring(y, { toValue: 0, useNativeDriver: true, friction: 8 }).start();
    const t = setTimeout(() => {
      Animated.timing(y, { toValue: 60, duration: 180, useNativeDriver: true })
        .start(() => onHide());
    }, 1400);
    return () => clearTimeout(t);
  }, [text]);
  if (!text) return null;
  return (
    <Animated.View style={[styles.toast, { transform: [{ translateY: y }] }]}>
      <Text style={styles.toastText}>{text}</Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  imgWrap: { aspectRatio: 1, backgroundColor: "#e6e6e6", alignItems: "center", justifyContent: "center" },
  img: { width: "100%", height: "100%" },
  body: { padding: spacing.lg, gap: 8 },
  store: { color: colors.store, fontWeight: "700", fontSize: 12 },
  name: { fontSize: 20, fontWeight: "800", color: colors.text },
  price: { fontSize: 18 },
  priceB: { fontWeight: "800", color: colors.text },
  old: { color: colors.textMuted, textDecorationLine: "line-through", fontSize: 14 },
  label: { color: colors.textMuted, marginTop: 8, fontSize: 13 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: { borderWidth: 1.5, borderColor: colors.secondaryBg, backgroundColor: colors.secondaryBg, borderRadius: radius.sm, paddingVertical: 8, paddingHorizontal: 16 },
  chipOn: { borderColor: colors.brand },
  chipText: { color: colors.text },
  chipTextOn: { color: colors.brand, fontWeight: "700" },
  desc: { color: colors.text, lineHeight: 20, marginTop: 8 },
  bar: {
    flexDirection: "row", gap: 10, padding: spacing.lg, paddingBottom: spacing.lg,
    borderTopWidth: 1, borderTopColor: colors.line, backgroundColor: colors.bg,
  },
  cartBtn: {
    flex: 1, borderWidth: 1.5, borderColor: colors.brand, borderRadius: radius.md,
    padding: 15, alignItems: "center",
  },
  cartText: { color: colors.brand, fontWeight: "800", fontSize: 15 },
  // "Sotib olish" — to'q yashil (rol-rang tizimi)
  buy: { flex: 1, backgroundColor: colors.store, borderRadius: radius.md, padding: 15, alignItems: "center" },
  buyText: { color: "#fff", fontWeight: "800", fontSize: 15 },
  disabled: { backgroundColor: colors.secondaryBg },
  toast: {
    position: "absolute", left: spacing.lg, right: spacing.lg, bottom: 90,
    backgroundColor: "rgba(26,26,26,0.92)", borderRadius: radius.md,
    paddingVertical: 12, paddingHorizontal: 16, alignItems: "center",
  },
  toastText: { color: "#fff", fontWeight: "700" },
});
