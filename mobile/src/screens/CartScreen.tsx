import React, { useState } from "react";
import { View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity, Alert } from "react-native";
import { api, money } from "../api";
import { colors, radius, spacing, font } from "../theme";
import { effPrice } from "../types";
import { useCart } from "../cart/CartContext";

const DELIVERY_FEE = 100;

export default function CartScreen({ navigation }: any) {
  const { lines, subtotal, changeQty, clear, keyOf } = useCart();
  const [manzil, setManzil] = useState("");
  const [busy, setBusy] = useState(false);
  const fee = lines.length ? DELIVERY_FEE : 0;
  const total = subtotal + fee;

  async function doCheckout(tel?: string) {
    const items = lines.map((l) => ({
      product_id: l.product.id, soni: l.soni,
      olcham: l.olcham || null, rang: l.rang || null,
    }));
    if (tel) await api("/api/confirm-phone", { method: "POST", body: { tel } });
    const { ok, status, data } = await api<any>("/api/checkout", {
      method: "POST",
      body: { items, yetkazish_turi: "kuryer", manzil: manzil.trim() },
    });
    if (ok) {
      const kodlar = (data.buyurtmalar || []).map((o: any) => o.kod).join(", ");
      clear();
      Alert.alert("✅ Buyurtma qabul qilindi", `Kod(lar): ${kodlar}`,
        [{ text: "OK", onPress: () => navigation.navigate("Buyurtmalar") }]);
    } else if (status === 428) {
      Alert.prompt?.("Telefon raqami", "Birinchi buyurtma uchun raqamingizni kiriting:",
        (v) => v && doCheckout(v));
      if (!Alert.prompt) Alert.alert("Telefon kerak", "Profil orqali telefon raqamingizni tasdiqlang.");
    } else if (status === 402) {
      Alert.alert("Balans yetarli emas", "Hisobingizni to'ldiring.",
        [{ text: "Balansга o'tish", onPress: () => navigation.navigate("Balans") }, { text: "Yopish" }]);
    } else {
      Alert.alert("Xatolik", data?.detail || "Buyurtma berilmadi.");
    }
  }

  async function checkout() {
    if (!lines.length) return;
    if (!manzil.trim()) return Alert.alert("Manzil", "Yetkazish manzilини kiriting.");
    setBusy(true);
    await doCheckout();
    setBusy(false);
  }

  if (!lines.length) {
    return (
      <View style={styles.empty}>
        <Text style={{ fontSize: 52 }}>🛒</Text>
        <Text style={styles.emptyTitle}>Savatingiz bo'sh</Text>
        <TouchableOpacity style={styles.primary} onPress={() => navigation.navigate("KatalogTab")}>
          <Text style={styles.primaryText}>Katalogni ko'rish</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={{ padding: spacing.lg }}>
        {lines.map((l) => (
          <View key={keyOf(l)} style={styles.row}>
            <View style={{ flex: 1 }}>
              <Text style={styles.rowName}>{l.product.nomi}</Text>
              {(l.olcham || l.rang) && <Text style={styles.variant}>{[l.olcham, l.rang].filter(Boolean).join(" · ")}</Text>}
              <Text style={styles.rowPrice}>{money(effPrice(l.product))} som</Text>
            </View>
            <View style={styles.qty}>
              <TouchableOpacity onPress={() => changeQty(keyOf(l), -1)} style={styles.qtyBtn}><Text style={styles.qtyBtnText}>−</Text></TouchableOpacity>
              <Text style={styles.qtyNum}>{l.soni}</Text>
              <TouchableOpacity onPress={() => changeQty(keyOf(l), 1)} style={styles.qtyBtn}><Text style={styles.qtyBtnText}>+</Text></TouchableOpacity>
            </View>
          </View>
        ))}

        <Text style={styles.label}>Yetkazish manzili:</Text>
        <TextInput style={styles.input} placeholder="Ko'cha, uy..." value={manzil} onChangeText={setManzil} />

        <View style={styles.summary}>
          <View style={styles.sumRow}><Text>Mahsulotlar:</Text><Text>{money(subtotal)} som</Text></View>
          <View style={styles.sumRow}><Text>🚚 Yetkazish:</Text><Text>{money(fee)} som</Text></View>
          <View style={[styles.sumRow, styles.totalRow]}><Text style={styles.totalT}>Jami:</Text><Text style={styles.totalV}>{money(total)} som</Text></View>
        </View>
      </ScrollView>
      <TouchableOpacity style={styles.checkout} onPress={checkout} disabled={busy}>
        <Text style={styles.checkoutText}>{busy ? "..." : "Buyurtma berish"}</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  empty: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: colors.bg },
  emptyTitle: { fontSize: font.h2, fontWeight: "700", color: colors.text },
  primary: { backgroundColor: colors.brand, borderRadius: radius.md, paddingVertical: 12, paddingHorizontal: 24 },
  primaryText: { color: "#fff", fontWeight: "800" },
  row: { flexDirection: "row", alignItems: "center", paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: colors.line },
  rowName: { fontWeight: "700", color: colors.text },
  variant: { color: colors.textMuted, fontSize: 12 },
  rowPrice: { color: colors.store, fontSize: 12, marginTop: 2 },
  qty: { flexDirection: "row", alignItems: "center", gap: 10 },
  qtyBtn: { width: 32, height: 32, borderRadius: 8, backgroundColor: colors.secondaryBg, alignItems: "center", justifyContent: "center" },
  qtyBtnText: { fontSize: 18, color: colors.text },
  qtyNum: { minWidth: 20, textAlign: "center", fontWeight: "700" },
  label: { marginTop: spacing.lg, marginBottom: 6, color: colors.textMuted },
  input: { borderWidth: 1, borderColor: colors.line, backgroundColor: colors.secondaryBg, borderRadius: radius.sm, padding: 12 },
  summary: { backgroundColor: colors.secondaryBg, borderRadius: radius.md, padding: 12, marginTop: spacing.lg, gap: 8 },
  sumRow: { flexDirection: "row", justifyContent: "space-between" },
  totalRow: { borderTopWidth: 1, borderTopColor: colors.line, paddingTop: 8 },
  totalT: { fontWeight: "800", fontSize: 16 },
  totalV: { fontWeight: "800", fontSize: 16, color: colors.gold },
  checkout: { backgroundColor: colors.brand, margin: spacing.lg, borderRadius: radius.md, padding: 15, alignItems: "center" },
  checkoutText: { color: "#fff", fontWeight: "800", fontSize: 15 },
});
