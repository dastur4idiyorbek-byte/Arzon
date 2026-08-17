import React from "react";
import { View, Text, StyleSheet, TouchableOpacity, Alert, ScrollView, Share } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors, radius, spacing, font, shadow , border } from "../theme";
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
      {/* Foydalanuvchi kartasi — balans YO'Q (to'lov har buyurtmaga alohida). */}
      <View style={styles.card}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>
            {(user?.ism || user?.email || "?").trim().charAt(0).toUpperCase()}
          </Text>
        </View>
        <Text style={styles.ism}>{user?.ism || user?.email}</Text>
        {!!user?.tel && <Text style={styles.tel}>{user.tel}</Text>}
      </View>

      <TouchableOpacity style={styles.panelBtn} onPress={() => navigation.navigate("Buyurtmalar")}>
        <Ionicons name="cube-outline" size={22} color={colors.brand} />
        <Text style={styles.panelText}>Buyurtmalarim</Text>
        <Ionicons name="chevron-forward" size={18} color={colors.textFaint} />
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

      <Text style={styles.roles}>Rollar: {roles.join(", ")}</Text>
      <TouchableOpacity style={[styles.btn, styles.out]} onPress={signOut}>
        <Text style={[styles.btnText, { color: colors.brand }]}>Chiqish</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bgSoft },
  card: {
    backgroundColor: colors.bg, borderRadius: radius.lg, padding: spacing.xl,
    alignItems: "center", gap: 8, ...border.hair,
  },
  avatar: {
    width: 64, height: 64, borderRadius: 32, backgroundColor: colors.brandSoft,
    alignItems: "center", justifyContent: "center",
  },
  avatarText: { fontSize: 26, fontWeight: "900", color: colors.brand },
  ism: { fontSize: font.h2, fontWeight: "800", color: colors.text },
  tel: { color: colors.textMuted, fontSize: font.small },
  label: { color: colors.gold, fontWeight: "700" },
  big: { fontSize: 34, fontWeight: "800", color: colors.gold },
  hint: { color: colors.textMuted, fontSize: 12, textAlign: "center" },
  btn: { backgroundColor: colors.brand, borderRadius: radius.md, paddingVertical: 15, alignItems: "center", marginTop: spacing.lg, ...shadow.md },
  out: { backgroundColor: colors.bg, borderWidth: 1.5, borderColor: colors.brand, shadowOpacity: 0, elevation: 0 },
  btnText: { color: "#fff", fontWeight: "800" },
  panels: { marginTop: spacing.xl, gap: 10 },
  panelsTitle: { fontWeight: "800", color: colors.text, fontSize: font.h2, marginBottom: 4 },
  panelBtn: {
    flexDirection: "row", alignItems: "center", gap: 12,
    backgroundColor: colors.bg, borderRadius: radius.md, padding: 16, ...border.hair,
  },
  panelText: { flex: 1, fontWeight: "700", color: colors.text },
  idCard: {
    flexDirection: "row", alignItems: "center", gap: 12,
    backgroundColor: colors.bg, borderRadius: radius.md, padding: 16,
    marginBottom: spacing.lg, ...border.hair,
  },
  idLabel: { color: colors.textMuted, fontSize: 12 },
  idValue: { fontSize: 24, fontWeight: "800", color: colors.brand, letterSpacing: 1 },
  idHint: { color: colors.textMuted, fontSize: 11, marginTop: 2 },
  profile: { textAlign: "center", fontWeight: "700", color: colors.text },
  roles: { textAlign: "center", color: colors.textMuted, marginBottom: 8 },
});
