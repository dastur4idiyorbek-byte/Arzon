/**
 * Admin — promo kodlar (4.1).
 *
 * Mijoz savatda kodni kiritsa, shu do'kon mahsulotlariga chegirma tushadi.
 * Kod + foiz + muddat belgilanadi; muddat qo'yilsa mijozda taymer ko'rinadi.
 */
import React, { useState } from "react";
import {
  View, Text, StyleSheet, TextInput, ScrollView, TouchableOpacity, Alert,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { api } from "../../api";
import { colors, radius, spacing, font, shadow } from "../../theme";
import { Btn } from "./PanelUI";

const MUDDATLAR: [string, number | null][] = [
  ["1 kun", 1], ["3 kun", 3], ["1 hafta", 7], ["1 oy", 30], ["Muddatsiz", null],
];

export default function AdminPromoScreen({ route, navigation }: any) {
  const { storeId, storeNomi } = route.params;
  const [kod, setKod] = useState("");
  const [foiz, setFoiz] = useState("10");
  const [kun, setKun] = useState<number | null>(7);
  const [busy, setBusy] = useState(false);

  /** Tasodifiy, o'qish oson kod (chalkash belgilarsiz: 0/O, 1/I yo'q). */
  function tasodifiy() {
    const belgilar = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    let k = "";
    for (let i = 0; i < 6; i++) {
      k += belgilar[Math.floor(Math.random() * belgilar.length)];
    }
    setKod(k);
  }

  async function yarat() {
    const k = kod.trim().toUpperCase();
    if (k.length < 3) return Alert.alert("Kod", "Kod kamida 3 belgidan iborat bo'lsin.");
    const f = Number(foiz);
    if (!f || f < 1 || f > 99) return Alert.alert("Foiz", "1 dan 99 gacha son kiriting.");

    const muddat = kun == null
      ? null
      : new Date(Date.now() + kun * 86400000).toISOString();

    setBusy(true);
    const { ok, data } = await api(`/api/admin/stores/${storeId}/promo`, {
      method: "POST",
      body: { kod: k, chegirma_foizi: f, muddat },
    });
    setBusy(false);
    if (ok) {
      Alert.alert(
        "✅ Promo yaratildi",
        `Kod: ${k}\nChegirma: ${f}%\n` +
          (kun == null ? "Muddatsiz" : `${kun} kun amal qiladi`) +
          "\n\nKodni mijozlarga tarqating — ular savatda kiritadi.",
        [{ text: "OK", onPress: () => navigation.goBack() }]
      );
    } else {
      Alert.alert("Xatolik", (data as any)?.detail || "Yaratilmadi.");
    }
  }

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.bgSoft }}
      contentContainerStyle={{ padding: spacing.lg, paddingBottom: 40 }}
    >
      <View style={styles.izohKarta}>
        <Ionicons name="pricetag" size={20} color={colors.brand} />
        <Text style={styles.izoh}>
          Promo kod <Text style={{ fontWeight: "800" }}>{storeNomi}</Text> do'koni
          mahsulotlariga chegirma beradi. Mijoz uni savatda kiritadi.
        </Text>
      </View>

      <Text style={styles.label}>Kod</Text>
      <View style={styles.kodRow}>
        <TextInput
          style={[styles.in, { flex: 1 }]}
          value={kod}
          onChangeText={(v) => setKod(v.toUpperCase())}
          placeholder="MASALAN: YOZ25"
          placeholderTextColor={colors.textFaint}
          autoCapitalize="characters"
          maxLength={32}
        />
        <TouchableOpacity style={styles.tasodif} onPress={tasodifiy}>
          <Ionicons name="dice-outline" size={20} color={colors.brand} />
        </TouchableOpacity>
      </View>

      <Text style={styles.label}>Chegirma foizi</Text>
      <View style={styles.foizlar}>
        {["5", "10", "15", "20", "30", "50"].map((f) => (
          <TouchableOpacity
            key={f}
            onPress={() => setFoiz(f)}
            style={[styles.foiz, foiz === f && styles.foizOn]}
          >
            <Text style={[styles.foizText, foiz === f && { color: "#fff" }]}>{f}%</Text>
          </TouchableOpacity>
        ))}
      </View>
      <TextInput
        style={[styles.in, { marginTop: 10 }]}
        value={foiz}
        onChangeText={setFoiz}
        keyboardType="numeric"
        placeholder="Boshqa foiz"
        placeholderTextColor={colors.textFaint}
      />

      <Text style={styles.label}>Amal qilish muddati</Text>
      <View style={styles.foizlar}>
        {MUDDATLAR.map(([nom, k]) => (
          <TouchableOpacity
            key={nom}
            onPress={() => setKun(k)}
            style={[styles.foiz, kun === k && styles.foizOn]}
          >
            <Text style={[styles.foizText, kun === k && { color: "#fff" }]}>{nom}</Text>
          </TouchableOpacity>
        ))}
      </View>
      {kun != null && (
        <Text style={styles.hint}>
          Mijozda sanovchi taymer ko'rinadi — bu xaridni tezlashtiradi.
        </Text>
      )}

      <Btn
        label={busy ? "Yaratilmoqda..." : "Promo kod yaratish"}
        onPress={yarat}
        disabled={busy}
        style={{ marginTop: spacing.xl }}
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  izohKarta: {
    flexDirection: "row", gap: 12, alignItems: "flex-start",
    backgroundColor: colors.brandSoft, borderRadius: radius.md, padding: 14,
  },
  izoh: { flex: 1, color: colors.text, fontSize: font.small, lineHeight: 19 },
  label: {
    color: colors.text, marginTop: spacing.xl, marginBottom: 10,
    fontWeight: "800", fontSize: font.h3,
  },
  kodRow: { flexDirection: "row", gap: 10 },
  in: {
    backgroundColor: colors.bg, borderRadius: radius.md, paddingHorizontal: 16,
    height: 52, color: colors.text, fontSize: 16, fontWeight: "700",
    letterSpacing: 1, ...shadow.sm,
  },
  tasodif: {
    width: 52, height: 52, borderRadius: radius.md, backgroundColor: colors.brandSoft,
    alignItems: "center", justifyContent: "center",
  },
  foizlar: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  foiz: {
    paddingHorizontal: 16, paddingVertical: 11, borderRadius: radius.sm,
    backgroundColor: colors.bg, ...shadow.xs,
  },
  foizOn: { backgroundColor: colors.brand },
  foizText: { fontWeight: "800", color: colors.text, fontSize: font.small },
  hint: { color: colors.textMuted, fontSize: font.small, marginTop: 10, lineHeight: 18 },
});
