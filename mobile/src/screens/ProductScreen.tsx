import React, { useState } from "react";
import { View, Text, StyleSheet, Image, ScrollView, TouchableOpacity, Alert } from "react-native";
import { money } from "../api";
import { colors, radius, spacing, font } from "../theme";
import { Product, effPrice } from "../types";
import { useCart } from "../cart/CartContext";

const parse = (s?: string | null) => (s || "").split(",").map((x) => x.trim()).filter(Boolean);

export default function ProductScreen({ route, navigation }: any) {
  const p: Product = route.params.product;
  const { add } = useCart();
  const olchamlar = parse(p.olcham);
  const ranglar = parse(p.rang);
  const [olcham, setOlcham] = useState<string | null>(olchamlar.length === 1 ? olchamlar[0] : null);
  const [rang, setRang] = useState<string | null>(ranglar.length === 1 ? ranglar[0] : null);
  const img = p.rasm_url || (p.rasm_urls && p.rasm_urls[0]);
  const sotuv = effPrice(p);

  function addToCart() {
    if (olchamlar.length && !olcham) return Alert.alert("O'lcham", "O'lchamni tanlang.");
    if (ranglar.length && !rang) return Alert.alert("Rang", "Rangni tanlang.");
    add(p, olcham, rang);
    Alert.alert("Savat", "Mahsulot savatga qo'shildi.", [
      { text: "Davom etish" },
      { text: "Savatga o'tish", onPress: () => navigation.navigate("Savat") },
    ]);
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
      <TouchableOpacity style={[styles.buy, p.tugadi && { opacity: 0.4 }]} disabled={!!p.tugadi} onPress={addToCart}>
        <Text style={styles.buyText}>{p.tugadi ? "Tugadi" : "🛒 Savatga qo'shish"}</Text>
      </TouchableOpacity>
    </View>
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
  buy: { backgroundColor: colors.brand, margin: spacing.lg, borderRadius: radius.md, padding: 15, alignItems: "center" },
  buyText: { color: "#fff", fontWeight: "800", fontSize: 15 },
});
