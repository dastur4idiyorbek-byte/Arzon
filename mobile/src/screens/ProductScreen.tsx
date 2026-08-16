/**
 * Mahsulot sahifasi — 2026 savdo me'yorlari.
 *
 *   • To'liq kenglikdagi rasm, ustida orqaga/ulashish tugmalari (suzuvchi).
 *   • Ma'lumot oppoq kartochkada, rasm ustiga chiqib turadi (qatlamlilik).
 *   • Pastda DOIMIY amal paneli — barmoq uchun qulay (thumb zone).
 *   • O'lcham/rang — tanlanganda aniq belgilangan chiplar.
 */
import React, { useState, useRef, useEffect } from "react";
import {
  View, Text, StyleSheet, Image, ScrollView, TouchableOpacity, Alert,
  Animated, Share, Dimensions,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { money } from "../api";
import { colors, radius, spacing, font, shadow, tracking } from "../theme";
import { Glass, ChegirmaTaymer } from "../ui/Glass";
import { Product, effPrice, rasmlar, nisbat } from "../types";
import { useCart } from "../cart/CartContext";

const { width: EKRAN } = Dimensions.get("window");
const parse = (s?: string | null) =>
  (s || "").split(",").map((x) => x.trim()).filter(Boolean);

export default function ProductScreen({ route, navigation }: any) {
  const p: Product = route.params.product;
  const { add, count } = useCart();
  const olchamlar = parse(p.olcham);
  const ranglar = parse(p.rang);
  const [olcham, setOlcham] = useState<string | null>(olchamlar.length === 1 ? olchamlar[0] : null);
  const [rang, setRang] = useState<string | null>(ranglar.length === 1 ? ranglar[0] : null);
  const [toast, setToast] = useState<string | null>(null);
  const suratlar = rasmlar(p);
  const nisbatSoni = nisbat(p);
  const [joriy, setJoriy] = useState(0);
  const sotuv = effPrice(p);
  const chegirma = !!p.skidka_foizi && p.skidka_foizi > 0;

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

  function addToCart() {
    if (!tanlovOk()) return;
    add(p, olcham, rang);
    setToast("Savatga qo'shildi");
  }

  function buyNow() {
    if (!tanlovOk()) return;
    add(p, olcham, rang);
    navigation.navigate("Savat");
  }

  const Chips = ({
    vals, sel, onSel,
  }: { vals: string[]; sel: string | null; onSel: (v: string) => void }) => (
    <View style={styles.chips}>
      {vals.map((v) => {
        const faol = sel === v;
        return (
          <TouchableOpacity
            key={v} onPress={() => onSel(v)} activeOpacity={0.8}
            style={[styles.chip, faol && styles.chipOn]}
          >
            <Text style={[styles.chipText, faol && styles.chipTextOn]}>{v}</Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );

  return (
    <View style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 24 }}>
        {/* Rasm karuseli — turli nisbatlarni qo'llab-quvvatlaydi */}
        <View style={[styles.imgWrap, { height: EKRAN / nisbatSoni }]}>
          {suratlar.length ? (
            <ScrollView
              horizontal
              pagingEnabled
              showsHorizontalScrollIndicator={false}
              onMomentumScrollEnd={(e) =>
                setJoriy(Math.round(e.nativeEvent.contentOffset.x / EKRAN))
              }
            >
              {suratlar.map((u, i) => (
                <Image
                  key={i}
                  source={{ uri: u }}
                  style={{ width: EKRAN, height: EKRAN / nisbatSoni }}
                  resizeMode="cover"
                />
              ))}
            </ScrollView>
          ) : (
            <Text style={{ fontSize: 72, opacity: 0.4 }}>🛍️</Text>
          )}

          {/* Suzuvchi shisha tugmalar */}
          <View style={styles.suzuvchi}>
            <Glass style={styles.yumaloq}>
              <TouchableOpacity style={styles.yumaloqIch} onPress={() => navigation.goBack()}>
                <Ionicons name="arrow-back" size={20} color={colors.text} />
              </TouchableOpacity>
            </Glass>
            <Glass style={styles.yumaloq}>
              <TouchableOpacity
                style={styles.yumaloqIch}
                onPress={() => Share.share({ message: `${p.nomi} — ${money(sotuv)} som (ARZON)` })}
              >
                <Ionicons name="share-social-outline" size={19} color={colors.text} />
              </TouchableOpacity>
            </Glass>
          </View>

          {/* Sahifa nuqtalari (bir nechta rasm bo'lsa) */}
          {suratlar.length > 1 && (
            <View style={styles.nuqtalar}>
              {suratlar.map((_, i) => (
                <View key={i} style={[styles.nuqta, i === joriy && styles.nuqtaFaol]} />
              ))}
            </View>
          )}

          {chegirma && (
            <View style={styles.saleTag}>
              <Text style={styles.saleText}>−{p.skidka_foizi}%</Text>
            </View>
          )}
        </View>

        {/* Ma'lumot — rasm ustiga chiqib turadi */}
        <View style={styles.body}>
          {!!p.store_nomi && (
            <View style={styles.storeRow}>
              <Ionicons name="storefront-outline" size={14} color={colors.store} />
              <Text style={styles.store}>{p.store_nomi}</Text>
            </View>
          )}
          <Text style={styles.name}>{p.nomi}</Text>

          <View style={styles.priceRow}>
            <Text style={styles.priceB}>{money(sotuv)}</Text>
            <Text style={styles.som}>som</Text>
            {sotuv < p.narxi && <Text style={styles.old}>{money(p.narxi)} som</Text>}
          </View>

          {/* Chegirma tugashiga qancha qolgani — shoshilish hissi */}
          {chegirma && !!p.skidka_muddati && (
            <View style={{ marginTop: 10 }}>
              <ChegirmaTaymer muddat={p.skidka_muddati} />
            </View>
          )}

          {olchamlar.length > 0 && (
            <>
              <Text style={styles.label}>O'lcham</Text>
              <Chips vals={olchamlar} sel={olcham} onSel={setOlcham} />
            </>
          )}
          {ranglar.length > 0 && (
            <>
              <Text style={styles.label}>Rang</Text>
              <Chips vals={ranglar} sel={rang} onSel={setRang} />
            </>
          )}

          {!!p.tavsif && (
            <>
              <Text style={styles.label}>Tavsif</Text>
              <Text style={styles.desc}>{p.tavsif}</Text>
            </>
          )}

          {p.miqdor != null && p.miqdor > 0 && p.miqdor <= 5 && (
            <View style={styles.oz}>
              <Ionicons name="flame-outline" size={15} color={colors.sale} />
              <Text style={styles.ozText}>Kam qoldi — {p.miqdor} dona</Text>
            </View>
          )}
        </View>
      </ScrollView>

      {/* Doimiy amal paneli */}
      <View style={styles.bar}>
        {p.tugadi ? (
          <View style={[styles.buy, styles.disabled]}>
            <Text style={styles.buyText}>Tugadi</Text>
          </View>
        ) : (
          <>
            <TouchableOpacity style={styles.cartBtn} onPress={addToCart} activeOpacity={0.85}>
              <Ionicons name="bag-add-outline" size={20} color={colors.brand} />
              {count > 0 && (
                <View style={styles.miniBadge}>
                  <Text style={styles.miniBadgeText}>{count}</Text>
                </View>
              )}
            </TouchableOpacity>
            <TouchableOpacity style={styles.buy} onPress={buyNow} activeOpacity={0.85}>
              <Text style={styles.buyText}>Sotib olish · {money(sotuv)} som</Text>
            </TouchableOpacity>
          </>
        )}
      </View>

      <Toast text={toast} onHide={() => setToast(null)} />
    </View>
  );
}

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
      <Text style={styles.toastText}>{text}</Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bgSoft },

  imgWrap: {
    width: EKRAN, backgroundColor: colors.secondaryBg,
    alignItems: "center", justifyContent: "center",
  },
  img: { width: "100%", height: "100%" },
  suzuvchi: {
    position: "absolute", top: spacing.md, left: spacing.lg, right: spacing.lg,
    flexDirection: "row", justifyContent: "space-between",
  },
  yumaloq: { width: 42, height: 42, borderRadius: 21 },
  yumaloqIch: { width: "100%", height: "100%", alignItems: "center", justifyContent: "center" },
  nuqtalar: {
    position: "absolute", bottom: 34, alignSelf: "center",
    flexDirection: "row", gap: 6,
  },
  nuqta: {
    width: 6, height: 6, borderRadius: 3,
    backgroundColor: "rgba(255,255,255,0.6)",
  },
  nuqtaFaol: { width: 20, backgroundColor: "#fff" },
  saleTag: {
    position: "absolute", left: spacing.lg, bottom: spacing.xl + 12,
    backgroundColor: colors.sale, paddingHorizontal: 12, paddingVertical: 6,
    borderRadius: radius.xs,
  },
  saleText: { color: "#fff", fontWeight: "900", fontSize: font.small },

  body: {
    backgroundColor: colors.bg, marginTop: -24,
    borderTopLeftRadius: radius.xl, borderTopRightRadius: radius.xl,
    padding: spacing.xl, paddingTop: spacing.lg, gap: 6,
  },
  storeRow: { flexDirection: "row", alignItems: "center", gap: 5 },
  store: { color: colors.store, fontWeight: "700", fontSize: font.small },
  name: {
    fontSize: font.h1, fontWeight: "800", color: colors.text,
    letterSpacing: tracking.h1, lineHeight: 30, marginTop: 4,
  },
  priceRow: { flexDirection: "row", alignItems: "baseline", gap: 6, marginTop: 8 },
  priceB: {
    fontSize: font.hero, fontWeight: "900", color: colors.text,
    letterSpacing: tracking.hero,
  },
  som: { fontSize: font.body, color: colors.textMuted },
  old: {
    color: colors.textFaint, textDecorationLine: "line-through",
    fontSize: font.small, marginLeft: 4,
  },

  label: {
    color: colors.text, marginTop: spacing.lg, marginBottom: 8,
    fontSize: font.h3, fontWeight: "800", letterSpacing: tracking.h2,
  },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    minWidth: 52, height: 42, justifyContent: "center", alignItems: "center",
    paddingHorizontal: 16, borderRadius: radius.sm,
    backgroundColor: colors.secondaryBg, borderWidth: 2, borderColor: "transparent",
  },
  chipOn: { backgroundColor: colors.bg, borderColor: colors.text },
  chipText: { color: colors.textMuted, fontWeight: "700" },
  chipTextOn: { color: colors.text },
  desc: { color: colors.textMuted, lineHeight: 22, fontSize: font.body },

  oz: {
    flexDirection: "row", alignItems: "center", gap: 6, marginTop: spacing.lg,
    backgroundColor: colors.saleSoft, borderRadius: radius.sm, padding: 12,
  },
  ozText: { color: colors.sale, fontWeight: "700", fontSize: font.small },

  bar: {
    flexDirection: "row", gap: 10, paddingHorizontal: spacing.lg,
    paddingTop: spacing.md, paddingBottom: spacing.lg,
    backgroundColor: colors.bg, borderTopWidth: 1, borderTopColor: colors.lineSoft,
  },
  cartBtn: {
    width: 56, height: 54, borderRadius: radius.md, backgroundColor: colors.brandSoft,
    alignItems: "center", justifyContent: "center",
  },
  miniBadge: {
    position: "absolute", top: 6, right: 6, minWidth: 18, height: 18,
    borderRadius: 9, backgroundColor: colors.sale,
    alignItems: "center", justifyContent: "center", paddingHorizontal: 4,
  },
  miniBadgeText: { color: "#fff", fontSize: 10, fontWeight: "800" },
  buy: {
    flex: 1, height: 54, backgroundColor: colors.store, borderRadius: radius.md,
    alignItems: "center", justifyContent: "center", ...shadow.md,
  },
  buyText: { color: "#fff", fontWeight: "800", fontSize: font.h3 },
  disabled: { backgroundColor: colors.textFaint, shadowOpacity: 0, elevation: 0 },

  toast: {
    position: "absolute", left: spacing.lg, right: spacing.lg, bottom: 90,
    flexDirection: "row", alignItems: "center", gap: 10,
    backgroundColor: "rgba(15,17,21,0.95)", borderRadius: radius.md,
    paddingVertical: 14, paddingHorizontal: 16, ...shadow.lg,
  },
  toastText: { color: "#fff", fontWeight: "600", fontSize: font.body },
});
