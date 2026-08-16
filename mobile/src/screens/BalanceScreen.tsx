import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Alert, ScrollView, Share } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { Ionicons } from "@expo/vector-icons";
import { api, money } from "../api";
import { colors, radius, spacing, font } from "../theme";
import { useAuth } from "../auth/AuthContext";

// Rol -> panel ekrani (App.tsx RootNav'да ro'yxatdan o'tган).
const PANELS: {
  role: string;
  screen: string;
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  color: string;
}[] = [
  { role: "admin", screen: "AdminHome", label: "🛠 Admin paneli", icon: "construct-outline", color: colors.store },
  { role: "moliya", screen: "MoliyaHome", label: "💰 Moliya paneli", icon: "cash-outline", color: colors.gold },
  { role: "menejer", screen: "MenejerHome", label: "👔 Menejer paneli", icon: "briefcase-outline", color: colors.brand },
];

export default function BalanceScreen({ navigation }: any) {
  const { signOut, user, roles } = useAuth();
  const [bal, setBal] = useState(0);

  const load = useCallback(async () => {
    const { ok, data } = await api<{ coin_balans: number }>("/api/balance");
    if (ok && data) setBal(data.coin_balans || 0);
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  const myPanels = PANELS.filter((p) => roles.includes(p.role));
  const arzonId = user?.arzon_id ?? user?.id;

  async function shareId() {
    try {
      await Share.share({
        message:
          `Mening ARZON ID: #${arzonId}\n` +
          `(${user?.ism || user?.email || ""})`.trim(),
      });
    } catch {
      Alert.alert("ARZON ID", `#${arzonId}`);
    }
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: spacing.lg, paddingBottom: 40 }}>
      <View style={styles.card}>
        <Text style={styles.label}>🪙 ACOM balansingiz</Text>
        <Text style={styles.big}>{money(bal)} ACOM</Text>
        <Text style={styles.hint}>1 ACOM = 1 som. Xaridlar shu balansdan amalga oshadi.</Text>
      </View>

      <TouchableOpacity style={styles.btn}
        onPress={() => Alert.alert("To'ldirish", "Balans to'ldirish (chek yuklash) — keyingi bosqichда.")}>
        <Text style={styles.btnText}>➕ Hisobni to'ldirish</Text>
      </TouchableOpacity>

      {myPanels.length > 0 && (
        <View style={styles.panels}>
          <Text style={styles.panelsTitle}>Boshqaruv panellari</Text>
          {myPanels.map((p) => (
            <TouchableOpacity key={p.role} style={styles.panelBtn}
              onPress={() => navigation.navigate(p.screen)}>
              <Ionicons name={p.icon} size={22} color={p.color} />
              <Text style={styles.panelText}>{p.label}</Text>
              <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
            </TouchableOpacity>
          ))}
        </View>
      )}

      <View style={{ height: spacing.xl }} />

      {/* ARZON ID — foydalanuvchining yagona raqami. Admin qilish uchun shu
          ID ulashiladi (Telegram/Gmail bilan kirganidan qat'i nazar). */}
      <TouchableOpacity style={styles.idCard} onPress={shareId} activeOpacity={0.7}>
        <View style={{ flex: 1 }}>
          <Text style={styles.idLabel}>Sizning ARZON ID</Text>
          <Text style={styles.idValue}>#{arzonId}</Text>
          <Text style={styles.idHint}>
            Admin qilinishingiz uchun shu ID'ni menejerga yuboring — bosing
          </Text>
        </View>
        <Ionicons name="share-social-outline" size={20} color={colors.brand} />
      </TouchableOpacity>

      <Text style={styles.profile}>{user?.ism || user?.email}</Text>
      <Text style={styles.roles}>Rollar: {roles.join(", ")}</Text>
      <TouchableOpacity style={[styles.btn, styles.out]} onPress={signOut}>
        <Text style={[styles.btnText, { color: colors.brand }]}>Chiqish</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  card: { backgroundColor: "rgba(201,151,26,0.10)", borderColor: "rgba(201,151,26,0.35)", borderWidth: 1, borderRadius: radius.lg, padding: spacing.xl, alignItems: "center", gap: 6 },
  label: { color: colors.gold, fontWeight: "700" },
  big: { fontSize: 34, fontWeight: "800", color: colors.gold },
  hint: { color: colors.textMuted, fontSize: 12, textAlign: "center" },
  btn: { backgroundColor: colors.brand, borderRadius: radius.md, padding: 14, alignItems: "center", marginTop: spacing.lg },
  out: { backgroundColor: colors.bg, borderWidth: 1.5, borderColor: colors.brand },
  btnText: { color: "#fff", fontWeight: "800" },
  panels: { marginTop: spacing.xl, gap: 10 },
  panelsTitle: { fontWeight: "800", color: colors.text, fontSize: font.h2, marginBottom: 4 },
  panelBtn: {
    flexDirection: "row", alignItems: "center", gap: 12,
    backgroundColor: colors.cardTop, borderWidth: 1, borderColor: colors.line,
    borderRadius: radius.md, padding: 16,
  },
  panelText: { flex: 1, fontWeight: "700", color: colors.text },
  idCard: {
    flexDirection: "row", alignItems: "center", gap: 12,
    backgroundColor: colors.secondaryBg, borderWidth: 1, borderColor: colors.line,
    borderRadius: radius.md, padding: 16, marginBottom: spacing.lg,
  },
  idLabel: { color: colors.textMuted, fontSize: 12 },
  idValue: { fontSize: 24, fontWeight: "800", color: colors.brand, letterSpacing: 1 },
  idHint: { color: colors.textMuted, fontSize: 11, marginTop: 2 },
  profile: { textAlign: "center", fontWeight: "700", color: colors.text },
  roles: { textAlign: "center", color: colors.textMuted, marginBottom: 8 },
});
