/**
 * Admin — pul yechish so'rovi (4.1). Do'kon balansidan Moliyaga so'rov.
 */
import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, TextInput, Alert } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { api, money } from "../../api";
import { colors, radius, spacing, font } from "../../theme";
import { Screen, Loader, Card, Btn } from "./PanelUI";

export default function AdminWithdrawScreen({ route, navigation }: any) {
  const { storeId } = route.params;
  const [bal, setBal] = useState<any>(null);
  const [summa, setSumma] = useState("");
  const [karta, setKarta] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const { ok, data } = await api(`/api/admin/stores/${storeId}/balance`);
    if (ok) setBal(data);
    setLoading(false);
  }, [storeId]);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  async function submit() {
    const s = Number(summa);
    if (!s || s <= 0) return Alert.alert("Summa", "To'g'ri summa kiriting.");
    if (s > (bal?.yechish_mumkin ?? 0)) return Alert.alert("Summa", "Yechish mumkin summadan ko'p.");
    if (karta.trim().length < 4) return Alert.alert("Karta", "Karta raqamini kiriting.");
    setBusy(true);
    const { ok, data } = await api(`/api/admin/stores/${storeId}/withdraw`, {
      method: "POST", body: { summa: s, karta_raqami: karta.trim() },
    });
    setBusy(false);
    if (ok) {
      Alert.alert("✅ So'rov yuborildi", "Moliya tez orada ko'rib chiqadi.",
        [{ text: "OK", onPress: () => navigation.goBack() }]);
    } else {
      Alert.alert("Xatolik", (data as any)?.detail || "Yuborilmadi.");
    }
  }

  if (loading) return <Loader />;

  return (
    <Screen>
      <Card style={{ backgroundColor: "rgba(201,151,26,0.10)", borderColor: "rgba(201,151,26,0.35)" }}>
        <Text style={styles.label}>Yechish mumkin</Text>
        <Text style={styles.big}>{money(bal?.yechish_mumkin ?? 0)} som</Text>
        <Text style={styles.muted}>Umumiy balans: {money(bal?.kutilayotgan_balans ?? 0)} som</Text>
      </Card>

      <Text style={styles.field}>Summa (som)</Text>
      <TextInput style={styles.in} value={summa} onChangeText={setSumma} keyboardType="numeric" placeholder="0" />
      <Text style={styles.field}>Karta raqami</Text>
      <TextInput style={styles.in} value={karta} onChangeText={setKarta} keyboardType="numeric" placeholder="8600 ..." />

      <Btn label={busy ? "Yuborilmoqda..." : "Pul yechish so'rovи"} onPress={submit} disabled={busy} tone="gold" style={{ marginTop: spacing.lg }} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  label: { color: colors.gold, fontWeight: "700" },
  big: { fontSize: 30, fontWeight: "800", color: colors.gold },
  muted: { color: colors.textMuted, fontSize: 12, marginTop: 4 },
  field: { color: colors.textMuted, marginTop: spacing.lg, marginBottom: 6, fontWeight: "600" },
  in: {
    borderWidth: 1, borderColor: colors.line, backgroundColor: colors.secondaryBg,
    borderRadius: radius.sm, padding: 12, color: colors.text,
  },
});
