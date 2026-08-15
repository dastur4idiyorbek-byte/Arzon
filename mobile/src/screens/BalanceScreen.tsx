import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Alert } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { api, money } from "../api";
import { colors, radius, spacing, font } from "../theme";
import { useAuth } from "../auth/AuthContext";

export default function BalanceScreen() {
  const { signOut, user, roles } = useAuth();
  const [bal, setBal] = useState(0);

  const load = useCallback(async () => {
    const { ok, data } = await api<{ coin_balans: number }>("/api/balance");
    if (ok && data) setBal(data.coin_balans || 0);
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.label}>🪙 ACOM balansingiz</Text>
        <Text style={styles.big}>{money(bal)} ACOM</Text>
        <Text style={styles.hint}>1 ACOM = 1 som. Xaridlar shu balansdan amalga oshadi.</Text>
      </View>

      <TouchableOpacity style={styles.btn}
        onPress={() => Alert.alert("To'ldirish", "Balans to'ldirish (chek yuklash) — keyingi bosqichда.")}>
        <Text style={styles.btnText}>➕ Hisobni to'ldirish</Text>
      </TouchableOpacity>

      <View style={{ flex: 1 }} />
      <Text style={styles.profile}>{user?.ism || user?.email}</Text>
      <Text style={styles.roles}>Rollar: {roles.join(", ")}</Text>
      <TouchableOpacity style={[styles.btn, styles.out]} onPress={signOut}>
        <Text style={[styles.btnText, { color: colors.brand }]}>Chiqish</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.lg },
  card: { backgroundColor: "rgba(201,151,26,0.10)", borderColor: "rgba(201,151,26,0.35)", borderWidth: 1, borderRadius: radius.lg, padding: spacing.xl, alignItems: "center", gap: 6 },
  label: { color: colors.gold, fontWeight: "700" },
  big: { fontSize: 34, fontWeight: "800", color: colors.gold },
  hint: { color: colors.textMuted, fontSize: 12, textAlign: "center" },
  btn: { backgroundColor: colors.brand, borderRadius: radius.md, padding: 14, alignItems: "center", marginTop: spacing.lg },
  out: { backgroundColor: colors.bg, borderWidth: 1.5, borderColor: colors.brand },
  btnText: { color: "#fff", fontWeight: "800" },
  profile: { textAlign: "center", fontWeight: "700", color: colors.text },
  roles: { textAlign: "center", color: colors.textMuted, marginBottom: 8 },
});
