/**
 * Balans to'ldirish (to'lov tizimi).
 *
 * Oqim: to'lov usulini tanlash -> karta raqamiga pul o'tkazish -> summa yozish
 * -> chek rasmini yuklash -> so'rov Moliyaga ketadi -> tasdiqlangach ACOM tushadi.
 *
 * Backend: GET /api/tolov-usullari, POST /api/topup-request (multipart).
 */
import React, { useCallback, useState } from "react";
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity, Image, Alert, ScrollView,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import * as Clipboard from "expo-clipboard";
import { api, money, API_URL, authHeader } from "../api";
import { colors, radius, spacing, font } from "../theme";
import { Loader } from "./panels/PanelUI";

type Usul = {
  id: number; turi: string; nomi: string; qiymat: string;
  egasi: string | null; qr_rasm_url: string | null; izoh: string | null;
};

export default function TopupScreen({ navigation }: any) {
  const [usullar, setUsullar] = useState<Usul[]>([]);
  const [tanlangan, setTanlangan] = useState<number | null>(null);
  const [summa, setSumma] = useState("");
  const [chek, setChek] = useState<ImagePicker.ImagePickerAsset | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const { ok, data } = await api<Usul[]>("/api/tolov-usullari");
    const list = ok && Array.isArray(data) ? data : [];
    setUsullar(list);
    setTanlangan((c) => c ?? (list[0]?.id ?? null));
    setLoading(false);
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  async function nusxa(matn: string) {
    await Clipboard.setStringAsync(matn);
    Alert.alert("✅ Nusxalandi", matn);
  }

  async function rasmTanla(kameradan: boolean) {
    const ruxsat = kameradan
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!ruxsat.granted) {
      return Alert.alert(
        "Ruxsat kerak",
        kameradan ? "Kameraga ruxsat bering." : "Galereyaga ruxsat bering."
      );
    }
    const natija = kameradan
      ? await ImagePicker.launchCameraAsync({ quality: 0.7 })
      : await ImagePicker.launchImageLibraryAsync({
          mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.7,
        });
    if (!natija.canceled && natija.assets?.[0]) setChek(natija.assets[0]);
  }

  async function yubor() {
    const s = Number(summa);
    if (!s || s <= 0) return Alert.alert("Summa", "To'g'ri summa kiriting.");
    if (!chek) return Alert.alert("Chek", "Chek rasmini yuklang.");

    // multipart/form-data — api() JSON yuboradi, shuning uchun to'g'ridan fetch.
    const fd = new FormData();
    fd.append("summa", String(s));
    if (tanlangan) fd.append("tolov_usuli_id", String(tanlangan));
    fd.append("chek", {
      uri: chek.uri,
      name: chek.fileName || "chek.jpg",
      type: chek.mimeType || "image/jpeg",
    } as any);

    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/topup-request`, {
        method: "POST",
        headers: { ...authHeader() }, // Content-Type'ni fetch o'zi qo'yadi (boundary bilan)
        body: fd,
      });
      const data = await res.json().catch(() => null);
      if (res.ok) {
        Alert.alert(
          "✅ So'rov yuborildi",
          "Moliya chekni ko'rib chiqadi. Tasdiqlangach balansingiz to'ladi.",
          [{ text: "OK", onPress: () => navigation.goBack() }]
        );
      } else {
        Alert.alert("Xatolik", (data as any)?.detail || `Xato kodi: ${res.status}`);
      }
    } catch {
      Alert.alert("Xatolik", "Internet yo'q yoki server javob bermadi.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Loader />;

  const u = usullar.find((x) => x.id === tanlangan);

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: spacing.lg, paddingBottom: 40 }}>
      <Text style={styles.step}>1. To'lov usulini tanlang</Text>
      {usullar.length === 0 ? (
        <View style={styles.warn}>
          <Text style={styles.warnText}>
            Hozircha to'lov usullari sozlanmagan. Iltimos, keyinroq urinib ko'ring.
          </Text>
        </View>
      ) : (
        <View style={styles.usullar}>
          {usullar.map((x) => (
            <TouchableOpacity key={x.id} onPress={() => setTanlangan(x.id)}
              style={[styles.usul, x.id === tanlangan && styles.usulOn]}>
              <Text style={[styles.usulNomi, x.id === tanlangan && { color: colors.brand }]}>
                {x.nomi}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      {!!u && (
        <View style={styles.karta}>
          <Text style={styles.kartaLabel}>Shu raqamga o'tkazing:</Text>
          <TouchableOpacity style={styles.kartaRow} onPress={() => nusxa(u.qiymat)}>
            <Text style={styles.kartaNum}>{u.qiymat}</Text>
            <Ionicons name="copy-outline" size={20} color={colors.brand} />
          </TouchableOpacity>
          {!!u.egasi && <Text style={styles.egasi}>👤 {u.egasi}</Text>}
          {!!u.izoh && <Text style={styles.izoh}>{u.izoh}</Text>}
          {!!u.qr_rasm_url && (
            <Image source={{ uri: u.qr_rasm_url }} style={styles.qr} resizeMode="contain" />
          )}
        </View>
      )}

      <Text style={styles.step}>2. O'tkazgan summangizni yozing</Text>
      <TextInput style={styles.input} value={summa} onChangeText={setSumma}
        keyboardType="numeric" placeholder="Masalan: 5000"
        placeholderTextColor={colors.textMuted} />
      {!!Number(summa) && (
        <Text style={styles.hisob}>
          Hisobingizga <Text style={styles.hisobB}>{money(Number(summa))} ACOM</Text> tushadi
        </Text>
      )}

      <Text style={styles.step}>3. Chek rasmini yuklang</Text>
      {chek ? (
        <View>
          <Image source={{ uri: chek.uri }} style={styles.chek} resizeMode="cover" />
          <TouchableOpacity style={styles.chekOchir} onPress={() => setChek(null)}>
            <Text style={styles.chekOchirText}>✕ Boshqa rasm tanlash</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <View style={styles.rasmTugma}>
          <TouchableOpacity style={styles.rasmBtn} onPress={() => rasmTanla(true)}>
            <Ionicons name="camera-outline" size={24} color={colors.brand} />
            <Text style={styles.rasmText}>Suratga olish</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.rasmBtn} onPress={() => rasmTanla(false)}>
            <Ionicons name="images-outline" size={24} color={colors.brand} />
            <Text style={styles.rasmText}>Galereyadan</Text>
          </TouchableOpacity>
        </View>
      )}

      <TouchableOpacity
        style={[styles.yubor, busy && { opacity: 0.6 }]}
        onPress={yubor} disabled={busy}
      >
        <Text style={styles.yuborText}>{busy ? "Yuborilmoqda..." : "So'rov yuborish"}</Text>
      </TouchableOpacity>
      <Text style={styles.eslatma}>
        So'rovni Moliya ko'rib chiqadi. Tasdiqlangach balansingiz avtomatik to'ladi
        va sizga bildirishnoma keladi.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  step: { fontWeight: "800", color: colors.text, fontSize: font.h2, marginTop: spacing.lg, marginBottom: 10 },
  warn: { backgroundColor: "rgba(224,30,30,0.08)", borderRadius: radius.md, padding: 14 },
  warnText: { color: colors.sale, fontWeight: "600" },
  usullar: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  usul: {
    paddingVertical: 10, paddingHorizontal: 16, borderRadius: 999,
    backgroundColor: colors.secondaryBg, borderWidth: 1.5, borderColor: colors.secondaryBg,
  },
  usulOn: { borderColor: colors.brand, backgroundColor: colors.cardTop },
  usulNomi: { fontWeight: "700", color: colors.textMuted },
  karta: {
    backgroundColor: colors.cardTop, borderWidth: 1, borderColor: colors.line,
    borderRadius: radius.lg, padding: 16, marginTop: 12, gap: 6,
  },
  kartaLabel: { color: colors.textMuted, fontSize: 12 },
  kartaRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  kartaNum: { fontSize: 20, fontWeight: "800", color: colors.text, letterSpacing: 1 },
  egasi: { color: colors.store, fontWeight: "600" },
  izoh: { color: colors.textMuted, fontSize: 12 },
  qr: { width: "100%", height: 180, marginTop: 8, borderRadius: radius.sm },
  input: {
    borderWidth: 1, borderColor: colors.line, backgroundColor: colors.secondaryBg,
    borderRadius: radius.sm, padding: 14, color: colors.text, fontSize: 16,
  },
  hisob: { color: colors.textMuted, marginTop: 6, fontSize: 13 },
  hisobB: { color: colors.gold, fontWeight: "800" },
  rasmTugma: { flexDirection: "row", gap: 10 },
  rasmBtn: {
    flex: 1, alignItems: "center", gap: 6, paddingVertical: 22,
    borderWidth: 1.5, borderColor: colors.brand, borderStyle: "dashed",
    borderRadius: radius.md,
  },
  rasmText: { color: colors.brand, fontWeight: "700" },
  chek: { width: "100%", height: 240, borderRadius: radius.md, backgroundColor: colors.secondaryBg },
  chekOchir: { alignSelf: "center", marginTop: 8, padding: 8 },
  chekOchirText: { color: colors.sale, fontWeight: "700" },
  yubor: {
    backgroundColor: colors.brand, borderRadius: radius.md, padding: 16,
    alignItems: "center", marginTop: spacing.xl,
  },
  yuborText: { color: "#fff", fontWeight: "800", fontSize: 15 },
  eslatma: { color: colors.textMuted, fontSize: 12, textAlign: "center", marginTop: 12, lineHeight: 18 },
});
