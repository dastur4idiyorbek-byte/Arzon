/**
 * Buyurtma to'lovi (balanssiz tizim).
 *
 * Oqim: buyurtma berilgach holati "tolov_kutilmoqda" bo'ladi -> mijoz shu
 * ekranda to'lov usulini tanlaydi, karta/hamyon raqamiga pul o'tkazadi va
 * chek rasmini SHU buyurtmaga yuklaydi -> Moliya tasdiqlaydi -> buyurtma
 * do'konga ketadi.
 *
 * Backend: GET /api/tolov-usullari, POST /api/orders/{id}/chek (multipart).
 */
import React, { useCallback, useState } from "react";
import {
  View, Text, StyleSheet, TouchableOpacity, Image, Alert, ScrollView,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import * as Clipboard from "expo-clipboard";
import { api, money, API_URL, authHeader } from "../api";
import { colors, radius, spacing, font, border } from "../theme";
import { toliqUrl } from "../types";
import { Loader } from "./panels/PanelUI";

type Usul = {
  id: number; turi: string; nomi: string; qiymat: string;
  egasi: string | null; qr_rasm_url: string | null; izoh: string | null;
};

/** To'lov turiga mos ikonka — mijoz ro'yxatdan darhol tanib olsin. */
function usulIcon(turi: string): keyof typeof Ionicons.glyphMap {
  const t = (turi || "").toLowerCase();
  if (t.includes("crypto") || t.includes("kripto")) return "logo-bitcoin";
  if (t.includes("naqd")) return "cash-outline";
  if (t.includes("bank")) return "business-outline";
  return "card-outline";
}

export default function OrderPaymentScreen({ route, navigation }: any) {
  const orderId: number = route.params?.orderId;
  const kod: string = route.params?.kod || "";
  const summa: number = Number(route.params?.summa || 0);

  const [usullar, setUsullar] = useState<Usul[]>([]);
  const [tanlangan, setTanlangan] = useState<number | null>(null);
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
    if (!chek) return Alert.alert("Chek", "Avval chek rasmini yuklang.");

    // multipart/form-data — api() JSON yuboradi, shuning uchun to'g'ridan fetch.
    const fd = new FormData();
    if (tanlangan) fd.append("tolov_usuli_id", String(tanlangan));
    fd.append("chek", {
      uri: chek.uri,
      name: chek.fileName || "chek.jpg",
      type: chek.mimeType || "image/jpeg",
    } as any);

    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/orders/${orderId}/chek`, {
        method: "POST",
        headers: { ...authHeader() }, // Content-Type'ni fetch o'zi qo'yadi (boundary bilan)
        body: fd,
      });
      const data = await res.json().catch(() => null);
      if (res.ok) {
        Alert.alert(
          "✅ Chek yuborildi",
          "Moliya to'lovni tekshiradi. Tasdiqlangach buyurtmangiz do'konga o'tadi " +
            "va sizga bildirishnoma keladi.",
          [{ text: "OK", onPress: () => navigation.navigate("Main", { screen: "Buyurtmalar" }) }]
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
      {/* To'lanadigan summa — ekranning eng muhim raqami */}
      <View style={styles.summaCard}>
        <Text style={styles.summaLabel}>To'lanadigan summa</Text>
        <Text style={styles.summaVal}>{money(summa)} som</Text>
        {!!kod && <Text style={styles.kod}>Buyurtma kodi: {kod}</Text>}
      </View>

      <Text style={styles.step}>1. To'lov usulini tanlang</Text>
      {usullar.length === 0 ? (
        <View style={styles.warn}>
          <Text style={styles.warnText}>
            Hozircha to'lov usullari sozlanmagan. Iltimos, keyinroq urinib ko'ring.
          </Text>
        </View>
      ) : (
        <View style={styles.usullar}>
          {usullar.map((x) => {
            const faol = x.id === tanlangan;
            return (
              <TouchableOpacity
                key={x.id}
                onPress={() => setTanlangan(x.id)}
                style={[styles.usul, faol && styles.usulOn]}
                activeOpacity={0.85}
              >
                <Ionicons
                  name={usulIcon(x.turi)}
                  size={18}
                  color={faol ? colors.brand : colors.textMuted}
                />
                <Text style={[styles.usulNomi, faol && { color: colors.brand }]}>
                  {x.nomi}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      )}

      {!!u && (
        <View style={styles.karta}>
          <Text style={styles.kartaLabel}>Shu raqamga o'tkazing:</Text>
          <TouchableOpacity style={styles.kartaRow} onPress={() => nusxa(u.qiymat)}>
            <Text style={styles.kartaNum} selectable>{u.qiymat}</Text>
            <Ionicons name="copy-outline" size={20} color={colors.brand} />
          </TouchableOpacity>
          {!!u.egasi && <Text style={styles.egasi}>👤 {u.egasi}</Text>}
          {!!u.izoh && <Text style={styles.izoh}>{u.izoh}</Text>}
          {!!u.qr_rasm_url && (
            <Image source={{ uri: toliqUrl(u.qr_rasm_url) || "" }} style={styles.qr} resizeMode="contain" />
          )}
        </View>
      )}

      <Text style={styles.step}>2. Chek rasmini yuklang</Text>
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
        style={[styles.yubor, (busy || !chek) && { opacity: 0.5 }]}
        onPress={yubor}
        disabled={busy || !chek}
        activeOpacity={0.85}
      >
        <Text style={styles.yuborText}>{busy ? "Yuborilmoqda..." : "Chekni yuborish"}</Text>
      </TouchableOpacity>
      <Text style={styles.eslatma}>
        Chekni Moliya ko'rib chiqadi. Tasdiqlangach buyurtmangiz do'konga o'tadi.
        Chekni keyinroq ham "Buyurtmalarim" bo'limidan yuklashingiz mumkin.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bgSoft },
  summaCard: {
    backgroundColor: colors.bg, borderRadius: radius.lg, padding: spacing.lg,
    alignItems: "center", gap: 4, ...border.hair,
  },
  summaLabel: { color: colors.textMuted, fontSize: font.small },
  summaVal: { fontSize: 32, fontWeight: "900", color: colors.gold },
  kod: { color: colors.textMuted, fontSize: font.small, letterSpacing: 1 },

  step: { fontWeight: "800", color: colors.text, fontSize: font.h2, marginTop: spacing.xl, marginBottom: 10 },
  warn: { backgroundColor: colors.saleSoft, borderRadius: radius.md, padding: 14 },
  warnText: { color: colors.sale, fontWeight: "600" },
  usullar: { gap: 8 },
  usul: {
    flexDirection: "row", alignItems: "center", gap: 10,
    paddingVertical: 14, paddingHorizontal: 16, borderRadius: radius.md,
    backgroundColor: colors.bg, ...border.hair,
  },
  usulOn: { borderColor: colors.brand, borderWidth: 1.5, backgroundColor: colors.brandSoft },
  usulNomi: { fontWeight: "700", color: colors.textMuted, fontSize: font.body },
  karta: {
    backgroundColor: colors.bg, borderRadius: radius.lg, padding: 16,
    marginTop: 12, gap: 6, ...border.hair,
  },
  kartaLabel: { color: colors.textMuted, fontSize: font.tiny },
  kartaRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  kartaNum: { flex: 1, fontSize: 19, fontWeight: "800", color: colors.text, letterSpacing: 1 },
  egasi: { color: colors.store, fontWeight: "600" },
  izoh: { color: colors.textMuted, fontSize: font.tiny },
  qr: { width: "100%", height: 180, marginTop: 8, borderRadius: radius.sm },

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
    backgroundColor: colors.brand, borderRadius: radius.md, paddingVertical: 16,
    alignItems: "center", marginTop: spacing.xl,
  },
  yuborText: { color: "#fff", fontWeight: "800", fontSize: font.body + 1 },
  eslatma: { color: colors.textMuted, fontSize: font.tiny, textAlign: "center", marginTop: 12, lineHeight: 18 },
});
