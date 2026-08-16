/**
 * Admin — mahsulot qo'shish/tahrirlash formasi (4.1).
 * route.params.product bo'lsa tahrir; bo'lmasa yangi.
 */
import React, { useState } from "react";
import {
  View, Text, StyleSheet, TextInput, ScrollView, TouchableOpacity, Alert, Image,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import { api, API_URL, authHeader } from "../../api";
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
  // Ko'p rasm: birinchisi asosiy (kartochkada ko'rinadi), qolganlari karuselda.
  const [suratlar, setSuratlar] = useState<string[]>(() => {
    const b = product?.rasm_url ? [product.rasm_url] : [];
    const q = (product?.rasm_urls || []).filter((u: string) => u !== product?.rasm_url);
    return [...b, ...q];
  });
  const [nisbat, setNisbat] = useState<string>(product?.rasm_nisbati || "1:1");
  const [muddat, setMuddat] = useState<string | null>(product?.skidka_muddati || null);
  const [miqdor, setMiqdor] = useState(product?.miqdor != null ? String(product.miqdor) : "");
  const [mahfiy, setMahfiy] = useState(product?.korinish === "mahfiy");
  const [busy, setBusy] = useState(false);
  const [yuklanmoqda, setYuklanmoqda] = useState(false);

  /** Nisbiy manzilni (/media/db/1) to'liq URL'ga aylantiradi. */
  function rasmKorinish(u: string) {
    return u.startsWith("http") ? u : API_URL + u;
  }

  /** Kamera yoki galereyadan rasm tanlab, serverga yuklaydi. */
  async function rasmTanla(kameradan: boolean) {
    const ruxsat = kameradan
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!ruxsat.granted) {
      return Alert.alert("Ruxsat kerak",
        kameradan ? "Kameraga ruxsat bering." : "Galereyaga ruxsat bering.");
    }
    const natija = kameradan
      ? await ImagePicker.launchCameraAsync({ quality: 0.7 })
      : await ImagePicker.launchImageLibraryAsync({
          mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.7,
        });
    if (natija.canceled || !natija.assets?.[0]) return;
    const asset = natija.assets[0];

    setYuklanmoqda(true);
    try {
      const fd = new FormData();
      fd.append("rasm", {
        uri: asset.uri,
        name: asset.fileName || "rasm.jpg",
        type: asset.mimeType || "image/jpeg",
      } as any);
      const res = await fetch(`${API_URL}/api/media/upload`, {
        method: "POST", headers: { ...authHeader() }, body: fd,
      });
      const data = await res.json().catch(() => null);
      if (res.ok && (data as any)?.url) setSuratlar((r) => [...r, (data as any).url]);
      else Alert.alert("Xatolik", (data as any)?.detail || "Rasm yuklanmadi.");
    } catch {
      Alert.alert("Xatolik", "Internet yo'q yoki server javob bermadi.");
    } finally {
      setYuklanmoqda(false);
    }
  }

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
      rasm_url: suratlar[0] || null,
      rasm_urls: suratlar.length ? suratlar : null,
      rasm_nisbati: nisbat,
      skidka_muddati: muddat,
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

      <Label t={`Mahsulot rasmlari (${suratlar.length}/10)`} />
      {suratlar.length > 0 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false}
          style={{ marginBottom: 10 }} contentContainerStyle={{ gap: 10 }}>
          {suratlar.map((u, i) => (
            <View key={u + i}>
              <Image source={{ uri: rasmKorinish(u) }} style={styles.kichikRasm} resizeMode="cover" />
              {i === 0 && (
                <View style={styles.asosiy}><Text style={styles.asosiyText}>Asosiy</Text></View>
              )}
              <TouchableOpacity
                style={styles.rasmX}
                onPress={() => setSuratlar((r) => r.filter((_, j) => j !== i))}
              >
                <Ionicons name="close" size={13} color="#fff" />
              </TouchableOpacity>
            </View>
          ))}
        </ScrollView>
      )}
      {suratlar.length < 10 && (
        <View style={styles.rasmTugma}>
          <TouchableOpacity style={styles.rasmBtn} onPress={() => rasmTanla(true)} disabled={yuklanmoqda}>
            <Ionicons name="camera-outline" size={24} color={colors.brand} />
            <Text style={styles.rasmText}>Suratga olish</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.rasmBtn} onPress={() => rasmTanla(false)} disabled={yuklanmoqda}>
            <Ionicons name="images-outline" size={24} color={colors.brand} />
            <Text style={styles.rasmText}>Galereyadan</Text>
          </TouchableOpacity>
        </View>
      )}
      {yuklanmoqda && <Text style={styles.yuklanmoqda}>Rasm yuklanmoqda...</Text>}

      <Label t="Rasm formati" />
      <View style={styles.nisbatlar}>
        {[["1:1", "Kvadrat"], ["4:3", "Gorizontal"], ["3:4", "Vertikal"],
          ["16:9", "Keng"], ["9:16", "Baland"]].map(([k, nom]) => (
          <TouchableOpacity key={k} onPress={() => setNisbat(k)}
            style={[styles.nisbat, nisbat === k && styles.nisbatOn]}>
            <Text style={[styles.nisbatText, nisbat === k && styles.nisbatTextOn]}>{nom}</Text>
            <Text style={[styles.nisbatKod, nisbat === k && { color: "#fff" }]}>{k}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {Number(skidka) > 0 && (
        <>
          <Label t="Chegirma qachon tugaydi" />
          <View style={styles.muddatlar}>
            {[["1 kun", 1], ["3 kun", 3], ["1 hafta", 7], ["1 oy", 30]].map(([nom, kun]) => {
              const iso = new Date(Date.now() + (kun as number) * 86400000).toISOString();
              const tanlangan = !!muddat &&
                Math.abs(new Date(muddat).getTime() - new Date(iso).getTime()) < 3600000;
              return (
                <TouchableOpacity key={nom as string} onPress={() => setMuddat(iso)}
                  style={[styles.muddatBtn, tanlangan && styles.muddatOn]}>
                  <Text style={[styles.muddatText, tanlangan && { color: "#fff" }]}>{nom}</Text>
                </TouchableOpacity>
              );
            })}
            {!!muddat && (
              <TouchableOpacity onPress={() => setMuddat(null)} style={styles.muddatBekor}>
                <Text style={styles.muddatBekorText}>Muddatsiz</Text>
              </TouchableOpacity>
            )}
          </View>
          <Text style={styles.muddatIzoh}>
            {muddat
              ? `Mijozga taymer ko'rinadi: ${new Date(muddat).toLocaleString("en-GB")} gacha`
              : "Muddat qo'yilsa, mijozda sanovchi taymer chiqadi va xarid tezlashadi."}
          </Text>
        </>
      )}

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
  kichikRasm: { width: 96, height: 96, borderRadius: radius.sm, backgroundColor: colors.secondaryBg },
  asosiy: {
    position: "absolute", left: 4, bottom: 4, backgroundColor: colors.store,
    paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6,
  },
  asosiyText: { color: "#fff", fontSize: 9, fontWeight: "800" },
  rasmX: {
    position: "absolute", right: -5, top: -5, width: 22, height: 22, borderRadius: 11,
    backgroundColor: colors.sale, alignItems: "center", justifyContent: "center",
  },
  nisbatlar: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  nisbat: {
    paddingHorizontal: 12, paddingVertical: 8, borderRadius: radius.sm,
    backgroundColor: colors.secondaryBg, alignItems: "center",
  },
  nisbatOn: { backgroundColor: colors.text },
  nisbatText: { fontWeight: "700", color: colors.text, fontSize: 12 },
  nisbatTextOn: { color: "#fff" },
  nisbatKod: { fontSize: 10, color: colors.textMuted },
  muddatlar: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  muddatBtn: {
    paddingHorizontal: 14, paddingVertical: 10, borderRadius: radius.sm,
    backgroundColor: colors.secondaryBg,
  },
  muddatOn: { backgroundColor: colors.sale },
  muddatText: { fontWeight: "700", color: colors.text, fontSize: 12 },
  muddatBekor: {
    paddingHorizontal: 14, paddingVertical: 10, borderRadius: radius.sm,
    borderWidth: 1.5, borderColor: colors.line,
  },
  muddatBekorText: { fontWeight: "700", color: colors.textMuted, fontSize: 12 },
  muddatIzoh: { color: colors.textMuted, fontSize: 12, marginTop: 8, lineHeight: 17 },
  rasmOchir: { alignSelf: "center", marginTop: 8, padding: 8 },
  rasmOchirText: { color: colors.sale, fontWeight: "700" },
  rasmTugma: { flexDirection: "row", gap: 10 },
  rasmBtn: {
    flex: 1, alignItems: "center", gap: 6, paddingVertical: 22,
    borderWidth: 1.5, borderColor: colors.brand, borderStyle: "dashed",
    borderRadius: radius.md,
  },
  rasmText: { color: colors.brand, fontWeight: "700" },
  yuklanmoqda: { color: colors.textMuted, textAlign: "center", marginTop: 8 },
  check: { flexDirection: "row", alignItems: "center", gap: 10, marginTop: spacing.lg },
  box: {
    width: 26, height: 26, borderRadius: 7, borderWidth: 1.5, borderColor: colors.brand,
    alignItems: "center", justifyContent: "center",
  },
  boxOn: { backgroundColor: colors.brand },
  checkText: { color: colors.text, fontWeight: "600" },
});
