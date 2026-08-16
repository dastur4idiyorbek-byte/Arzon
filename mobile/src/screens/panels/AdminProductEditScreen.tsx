/**
 * Admin — mahsulot qo'shish/tahrirlash formasi (4.1).
 * route.params.product bo'lsa tahrir; bo'lmasa yangi.
 */
import React, { useState } from "react";
import {
  View, Text, StyleSheet, TextInput, ScrollView, TouchableOpacity, Alert,
} from "react-native";
import { api } from "../../api";
import { colors, radius, spacing, font } from "../../theme";
import { Btn } from "./PanelUI";

export default function AdminProductEditScreen({ route, navigation }: any) {
  const { storeId, product } = route.params || {};
  const edit = !!product;
  const [nomi, setNomi] = useState(product?.nomi || "");
  const [narxi, setNarxi] = useState(product ? String(product.narxi) : "");
  const [skidka, setSkidka] = useState(product?.skidka_foizi ? String(product.skidka_foizi) : "");
  const [olcham, setOlcham] = useState(product?.olcham || "");
  const [rang, setRang] = useState(product?.rang || "");
  const [tavsif, setTavsif] = useState(product?.tavsif || "");
  const [rasm, setRasm] = useState(product?.rasm_url || "");
  const [miqdor, setMiqdor] = useState(product?.miqdor != null ? String(product.miqdor) : "");
  const [mahfiy, setMahfiy] = useState(product?.korinish === "mahfiy");
  const [busy, setBusy] = useState(false);

  async function save() {
    if (!nomi.trim()) return Alert.alert("Nomi", "Mahsulot nomini kiriting.");
    const narxNum = Number(narxi);
    if (!narxNum || narxNum < 0) return Alert.alert("Narxi", "To'g'ri narx kiriting.");
    const body: any = {
      nomi: nomi.trim(),
      narxi: narxNum,
      skidka_foizi: skidka ? Math.min(99, Math.max(0, Number(skidka) || 0)) : 0,
      olcham: olcham.trim() || null,
      rang: rang.trim() || null,
      tavsif: tavsif.trim() || null,
      rasm_url: rasm.trim() || null,
      korinish: mahfiy ? "mahfiy" : "ommaviy",
      miqdor: miqdor.trim() === "" ? null : Math.max(0, Number(miqdor) || 0),
    };
    setBusy(true);
    const res = edit
      ? await api(`/api/admin/products/${product.id}`, { method: "PATCH", body })
      : await api(`/api/admin/stores/${storeId}/products`, { method: "POST", body });
    setBusy(false);
    if (res.ok) {
      Alert.alert("✅ Saqlandi", edit ? "Mahsulot yangilandi." : "Mahsulot qo'shildi.",
        [{ text: "OK", onPress: () => navigation.goBack() }]);
    } else {
      Alert.alert("Xatolik", (res.data as any)?.detail || "Saqlanmadi.");
    }
  }

  return (
    <ScrollView style={{ backgroundColor: colors.bg }} contentContainerStyle={{ padding: spacing.lg }}>
      <Text style={styles.h}>{edit ? "Mahsulotni tahrirlash" : "Yangi mahsulot"}</Text>

      <Label t="Nomi *" />
      <TextInput style={styles.in} value={nomi} onChangeText={setNomi} placeholder="Masalan: Ko'ylak" />

      <Label t="Narxi (som) *" />
      <TextInput style={styles.in} value={narxi} onChangeText={setNarxi} keyboardType="numeric" placeholder="0" />

      <Label t="Chegirma (%)" />
      <TextInput style={styles.in} value={skidka} onChangeText={setSkidka} keyboardType="numeric" placeholder="0" />

      <View style={styles.two}>
        <View style={{ flex: 1 }}>
          <Label t="O'lcham" />
          <TextInput style={styles.in} value={olcham} onChangeText={setOlcham} placeholder="S,M,L" />
        </View>
        <View style={{ flex: 1 }}>
          <Label t="Rang" />
          <TextInput style={styles.in} value={rang} onChangeText={setRang} placeholder="qora,oq" />
        </View>
      </View>

      <Label t="Miqdor (bo'sh = cheksiz)" />
      <TextInput style={styles.in} value={miqdor} onChangeText={setMiqdor} keyboardType="numeric" placeholder="cheksiz" />

      <Label t="Rasm URL" />
      <TextInput style={styles.in} value={rasm} onChangeText={setRasm} placeholder="https://..." autoCapitalize="none" />

      <Label t="Tavsif" />
      <TextInput style={[styles.in, { height: 90, textAlignVertical: "top" }]} value={tavsif}
        onChangeText={setTavsif} placeholder="Mahsulot haqida..." multiline />

      <TouchableOpacity style={styles.check} onPress={() => setMahfiy((v) => !v)}>
        <View style={[styles.box, mahfiy && styles.boxOn]}>
          {mahfiy && <Text style={{ color: "#fff", fontWeight: "900" }}>✓</Text>}
        </View>
        <Text style={styles.checkText}>🔒 Mahfiy mahsulot (faqat kod bilan)</Text>
      </TouchableOpacity>

      <Btn label={busy ? "Saqlanmoqda..." : "Saqlash"} onPress={save} disabled={busy} style={{ marginTop: spacing.lg }} />
    </ScrollView>
  );
}

function Label({ t }: { t: string }) {
  return <Text style={styles.label}>{t}</Text>;
}

const styles = StyleSheet.create({
  h: { fontSize: font.h1, fontWeight: "800", color: colors.text, marginBottom: spacing.md },
  label: { color: colors.textMuted, marginTop: spacing.md, marginBottom: 6, fontWeight: "600" },
  in: {
    borderWidth: 1, borderColor: colors.line, backgroundColor: colors.secondaryBg,
    borderRadius: radius.sm, padding: 12, color: colors.text,
  },
  two: { flexDirection: "row", gap: 12 },
  check: { flexDirection: "row", alignItems: "center", gap: 10, marginTop: spacing.lg },
  box: {
    width: 26, height: 26, borderRadius: 7, borderWidth: 1.5, borderColor: colors.brand,
    alignItems: "center", justifyContent: "center",
  },
  boxOn: { backgroundColor: colors.brand },
  checkText: { color: colors.text, fontWeight: "600" },
});
