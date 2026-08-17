import React, { useState } from "react";
import {
  View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity, Alert, Image,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { api, money } from "../api";
import { colors, radius, spacing, font, shadow , border } from "../theme";
import { effPrice, rasmUrl } from "../types";
import { useCart } from "../cart/CartContext";
import { usePrompt } from "../ui/Prompt";
import { ChegirmaTaymer } from "../ui/Glass";

const DELIVERY_FEE = 100;

export default function CartScreen({ navigation }: any) {
  const { lines, subtotal, changeQty, clear, keyOf } = useCart();
  const [manzil, setManzil] = useState("");
  const [busy, setBusy] = useState(false);
  const prompt = usePrompt();
  const [promo, setPromo] = useState("");
  const [promoHolat, setPromoHolat] = useState<any>(null);
  const [promoBusy, setPromoBusy] = useState(false);

  const fee = lines.length ? DELIVERY_FEE : 0;
  // Promo faqat o'ziga tegishli do'kon mahsulotlariga tushadi.
  const promoChegirma = promoHolat?.ok
    ? lines
        .filter((l) => l.product.store_id === promoHolat.store_id)
        .reduce((s, l) => s + effPrice(l.product) * l.soni, 0) *
      (promoHolat.chegirma_foizi / 100)
    : 0;
  const total = Math.max(0, subtotal - promoChegirma) + fee;

  /** Promo kodni buyurtmadan oldin tekshiradi (mijoz darhol javob ko'rsin). */
  async function promoTekshir() {
    const kod = promo.trim();
    if (!kod) return;
    setPromoBusy(true);
    const storeIds = Array.from(new Set(lines.map((l) => l.product.store_id)));
    const { ok, data } = await api<any>("/api/promo/check", {
      method: "POST", body: { kod, store_ids: storeIds },
    });
    setPromoBusy(false);
    if (ok && data) setPromoHolat(data);
    else setPromoHolat({ ok: false, sabab: "Tekshirib bo'lmadi. Internetni tekshiring." });
  }

  async function doCheckout(tel?: string) {
    const items = lines.map((l) => ({
      product_id: l.product.id, soni: l.soni,
      olcham: l.olcham || null, rang: l.rang || null,
    }));
    if (tel) await api("/api/confirm-phone", { method: "POST", body: { tel } });
    const { ok, status, data } = await api<any>("/api/checkout", {
      method: "POST",
      body: {
        items, yetkazish_turi: "kuryer", manzil: manzil.trim(),
        promo_kod: promoHolat?.ok ? promoHolat.kod : undefined,
      },
    });
    if (ok) {
      const kodlar = (data.buyurtmalar || []).map((o: any) => o.kod).join(", ");
      clear();
      Alert.alert("✅ Buyurtma qabul qilindi", `Kod(lar): ${kodlar}`,
        [{ text: "OK", onPress: () => navigation.navigate("Buyurtmalar") }]);
    } else if (status === 428) {
      // Birinchi buyurtma — telefon raqami talab qilinadi (rule 8, 2-bosqich).
      const t = await prompt({
        title: "Telefon raqami",
        message: "Birinchi buyurtma uchun raqamingizni kiriting:",
        placeholder: "+996 ...",
        keyboardType: "phone-pad",
        submitLabel: "Tasdiqlash",
      });
      if (t && t.trim()) await doCheckout(t.trim());
    } else if (status === 402) {
      Alert.alert("Balans yetarli emas", "Hisobingizni to'ldiring.", [
        { text: "Hisobni to'ldirish", onPress: () => navigation.navigate("Topup") },
        { text: "Yopish" },
      ]);
    } else {
      Alert.alert("Xatolik", data?.detail || "Buyurtma berilmadi.");
    }
  }

  async function checkout() {
    if (!lines.length) return;
    if (!manzil.trim()) return Alert.alert("Manzil", "Yetkazish manzilini kiriting.");
    setBusy(true);
    await doCheckout();
    setBusy(false);
  }

  if (!lines.length) {
    return (
      <View style={styles.empty}>
        <Text style={{ fontSize: 56 }}>🛒</Text>
        <Text style={styles.emptyTitle}>Savatingiz bo'sh</Text>
        <Text style={styles.emptyHint}>Katalogdan yoqqan mahsulotni tanlang.</Text>
        <TouchableOpacity style={styles.primary} onPress={() => navigation.navigate("KatalogTab")}>
          <Text style={styles.primaryText}>Katalogni ko'rish</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: spacing.xl }}>
        {/* Mahsulotlar */}
        <View style={styles.card}>
          {lines.map((l, i) => {
            const img = rasmUrl(l.product);
            return (
              <View key={keyOf(l)} style={[styles.row, i > 0 && styles.rowLine]}>
                <View style={styles.thumb}>
                  {img ? (
                    <Image source={{ uri: img }} style={styles.thumbImg} resizeMode="cover" />
                  ) : (
                    <Text style={{ fontSize: 22 }}>🛍️</Text>
                  )}
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.rowName} numberOfLines={2}>{l.product.nomi}</Text>
                  {(l.olcham || l.rang) && (
                    <Text style={styles.variant}>
                      {[l.olcham, l.rang].filter(Boolean).join(" · ")}
                    </Text>
                  )}
                  <Text style={styles.rowPrice}>{money(effPrice(l.product))} som</Text>
                </View>
                <View style={styles.qty}>
                  <TouchableOpacity onPress={() => changeQty(keyOf(l), -1)} style={styles.qtyBtn}>
                    <Ionicons
                      name={l.soni === 1 ? "trash-outline" : "remove"}
                      size={16}
                      color={l.soni === 1 ? colors.sale : colors.text}
                    />
                  </TouchableOpacity>
                  <Text style={styles.qtyNum}>{l.soni}</Text>
                  <TouchableOpacity onPress={() => changeQty(keyOf(l), 1)} style={styles.qtyBtn}>
                    <Ionicons name="add" size={16} color={colors.text} />
                  </TouchableOpacity>
                </View>
              </View>
            );
          })}
        </View>

        {/* Manzil */}
        <Text style={styles.label}>Yetkazish manzili</Text>
        <View style={styles.inputWrap}>
          <Ionicons name="location-outline" size={18} color={colors.textFaint} />
          <TextInput
            style={styles.input}
            placeholder="Ko'cha, uy, orientir..."
            placeholderTextColor={colors.textFaint}
            value={manzil}
            onChangeText={setManzil}
          />
        </View>

        {/* Promo kod */}
        <Text style={styles.label}>Promo kod</Text>
        <View style={styles.promoRow}>
          <View style={styles.promoInputWrap}>
            <Ionicons name="pricetag-outline" size={18} color={colors.textFaint} />
            <TextInput
              style={styles.input}
              placeholder="Kodni kiriting"
              placeholderTextColor={colors.textFaint}
              value={promo}
              onChangeText={(v) => { setPromo(v); setPromoHolat(null); }}
              autoCapitalize="characters"
            />
          </View>
          <TouchableOpacity
            style={[styles.promoBtn, (!promo.trim() || promoBusy) && { opacity: 0.5 }]}
            onPress={promoTekshir}
            disabled={!promo.trim() || promoBusy}
            activeOpacity={0.85}
          >
            <Text style={styles.promoBtnText}>{promoBusy ? "..." : "Qo'llash"}</Text>
          </TouchableOpacity>
        </View>
        {!!promoHolat && (
          <View style={[styles.promoJavob, promoHolat.ok ? styles.promoOk : styles.promoXato]}>
            <Ionicons
              name={promoHolat.ok ? "checkmark-circle" : "alert-circle"}
              size={16}
              color={promoHolat.ok ? colors.store : colors.sale}
            />
            <Text style={[styles.promoJavobText, { color: promoHolat.ok ? colors.store : colors.sale }]}>
              {promoHolat.ok
                ? `${promoHolat.chegirma_foizi}% chegirma qo'llandi` +
                  (promoHolat.store_nomi ? ` — ${promoHolat.store_nomi}` : "")
                : promoHolat.sabab}
            </Text>
          </View>
        )}
        {promoHolat?.ok && !!promoHolat.muddat && (
          <View style={{ marginTop: 8 }}>
            <ChegirmaTaymer muddat={promoHolat.muddat} />
          </View>
        )}

        {/* Hisob-kitob */}
        <View style={styles.summary}>
          <View style={styles.sumRow}>
            <Text style={styles.sumLabel}>Mahsulotlar</Text>
            <Text style={styles.sumVal}>{money(subtotal)} som</Text>
          </View>
          {promoChegirma > 0 && (
            <View style={styles.sumRow}>
              <Text style={[styles.sumLabel, { color: colors.store }]}>
                Promo ({promoHolat.chegirma_foizi}%)
              </Text>
              <Text style={[styles.sumVal, { color: colors.store }]}>
                −{money(promoChegirma)} som
              </Text>
            </View>
          )}
          <View style={styles.sumRow}>
            <Text style={styles.sumLabel}>🚚 Yetkazish</Text>
            <Text style={styles.sumVal}>{money(fee)} som</Text>
          </View>
          <View style={[styles.sumRow, styles.totalRow]}>
            <Text style={styles.totalT}>Jami</Text>
            <Text style={styles.totalV}>{money(total)} som</Text>
          </View>
        </View>
      </ScrollView>

      {/* Pastki panel */}
      <View style={styles.bar}>
        <View>
          <Text style={styles.barLabel}>Jami</Text>
          <Text style={styles.barTotal}>{money(total)} som</Text>
        </View>
        <TouchableOpacity
          style={[styles.checkout, busy && { opacity: 0.6 }]}
          onPress={checkout}
          disabled={busy}
          activeOpacity={0.85}
        >
          <Text style={styles.checkoutText}>{busy ? "Yuborilmoqda..." : "Buyurtma berish"}</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bgSoft },
  empty: {
    flex: 1, alignItems: "center", justifyContent: "center", gap: 10,
    backgroundColor: colors.bgSoft, paddingHorizontal: spacing.xl,
  },
  emptyTitle: { fontSize: font.h2, fontWeight: "800", color: colors.text },
  emptyHint: { color: colors.textMuted, textAlign: "center" },
  primary: {
    backgroundColor: colors.brand, borderRadius: radius.md,
    paddingVertical: 14, paddingHorizontal: 28, marginTop: 8,
  },
  primaryText: { color: "#fff", fontWeight: "800" },

  card: { backgroundColor: colors.bg, borderRadius: radius.lg, padding: spacing.md, ...border.hair },
  row: { flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: 12 },
  rowLine: { borderTopWidth: 1, borderTopColor: colors.lineSoft },
  thumb: {
    width: 56, height: 56, borderRadius: radius.sm, backgroundColor: colors.secondaryBg,
    alignItems: "center", justifyContent: "center", overflow: "hidden",
  },
  thumbImg: { width: "100%", height: "100%" },
  rowName: { fontWeight: "700", color: colors.text, fontSize: font.body },
  variant: { color: colors.textMuted, fontSize: font.tiny, marginTop: 2 },
  rowPrice: { color: colors.store, fontSize: font.small, marginTop: 3, fontWeight: "700" },
  qty: {
    flexDirection: "row", alignItems: "center", gap: 4,
    backgroundColor: colors.secondaryBg, borderRadius: radius.pill, padding: 3,
  },
  qtyBtn: { width: 30, height: 30, borderRadius: 15, backgroundColor: colors.bg, alignItems: "center", justifyContent: "center" },
  qtyNum: { minWidth: 22, textAlign: "center", fontWeight: "800", color: colors.text },

  label: { marginTop: spacing.xl, marginBottom: 8, color: colors.text, fontWeight: "800", fontSize: font.h3 },
  inputWrap: {
    flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: colors.bg,
    borderRadius: radius.md, paddingHorizontal: 14, height: 50, ...border.hair,
  },
  input: { flex: 1, color: colors.text, fontSize: font.body, padding: 0 },
  promoRow: { flexDirection: "row", gap: 10 },
  promoInputWrap: {
    flex: 1, flexDirection: "row", alignItems: "center", gap: 8,
    backgroundColor: colors.bg, borderRadius: radius.md,
    paddingHorizontal: 14, height: 50, ...border.hair,
  },
  promoBtn: {
    paddingHorizontal: 20, height: 50, borderRadius: radius.md,
    backgroundColor: colors.text, alignItems: "center", justifyContent: "center",
  },
  promoBtnText: { color: "#fff", fontWeight: "800", fontSize: font.small },
  promoJavob: {
    flexDirection: "row", alignItems: "center", gap: 7, marginTop: 10,
    borderRadius: radius.sm, padding: 11,
  },
  promoOk: { backgroundColor: colors.storeSoft },
  promoXato: { backgroundColor: colors.saleSoft },
  promoJavobText: { flex: 1, fontWeight: "700", fontSize: font.small },

  summary: { backgroundColor: colors.bg, borderRadius: radius.lg, padding: spacing.lg, marginTop: spacing.lg, gap: 10, ...border.hair },
  sumRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  sumLabel: { color: colors.textMuted },
  sumVal: { color: colors.text, fontWeight: "600" },
  totalRow: { borderTopWidth: 1, borderTopColor: colors.lineSoft, paddingTop: 10 },
  totalT: { fontWeight: "900", fontSize: font.h2, color: colors.text },
  totalV: { fontWeight: "900", fontSize: font.h2, color: colors.gold },

  bar: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    gap: spacing.md, paddingHorizontal: spacing.lg, paddingVertical: spacing.md,
    backgroundColor: colors.bg, borderTopWidth: 1, borderTopColor: colors.line,
  },
  barLabel: { color: colors.textMuted, fontSize: font.tiny },
  barTotal: { fontWeight: "900", fontSize: font.h2, color: colors.gold },
  checkout: {
    flex: 1, maxWidth: 220, backgroundColor: colors.brand, borderRadius: radius.md,
    paddingVertical: 15, alignItems: "center",
  },
  checkoutText: { color: "#fff", fontWeight: "800", fontSize: font.body + 1 },
});
