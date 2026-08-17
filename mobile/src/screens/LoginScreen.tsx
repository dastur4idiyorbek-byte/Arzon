import React, { useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView, Alert, Platform, Image,
} from "react-native";
import { api, xatoMatni } from "../api";
import { colors, radius, spacing, font, shadow } from "../theme";
import { useAuth, AuthUser } from "../auth/AuthContext";

type AuthResp = { token: string; user: AuthUser; roles: string[] };

export default function LoginScreen() {
  const { signInWithToken } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [parol, setParol] = useState("");
  const [ism, setIsm] = useState("");
  const [busy, setBusy] = useState(false);

  async function submitEmail() {
    if (!email.trim() || parol.length < 6) {
      Alert.alert("Diqqat", "Email va kamida 6 belgili parol kiriting.");
      return;
    }
    setBusy(true);
    const path = mode === "register" ? "/api/auth/register" : "/api/auth/login";
    const body = mode === "register"
      ? { email: email.trim(), parol, ism: ism.trim() || undefined }
      : { email: email.trim(), parol };
    const { ok, status, data } = await api<AuthResp>(path, { method: "POST", body });
    setBusy(false);
    if (ok && data) {
      await signInWithToken(data.token, data.user, data.roles);
    } else {
      Alert.alert("Kirib bo'lmadi", xatoMatni(status, data));
    }
  }

  async function forgot() {
    if (!email.trim()) {
      Alert.alert("Email kiriting", "Parolni tiklash uchun avval email kiriting.");
      return;
    }
    const { ok } = await api("/api/auth/forgot", { method: "POST", body: { email: email.trim() } });
    Alert.alert(ok ? "Yuborildi" : "Xatolik",
      ok ? "Agar email ro'yxatdan o'tган bo'lsa, tiklash yo'riqnomasi yuboriladi."
         : "Qayta urinib ko'ring.");
  }

  function socialSoon(nomi: string) {
    Alert.alert(nomi, `${nomi} bilan kirish 6-bosqich (build) sozlashida yoqiladi.`);
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Image source={require("../../assets/icon.png")} style={styles.logoImg} />
      <Text style={styles.logo}>ARZON</Text>
      <Text style={styles.sub}>Arzon narx · Sifatli mahsulot · Tez yetkazish</Text>

      <View style={styles.tabs}>
        <TouchableOpacity onPress={() => setMode("login")} style={[styles.tab, mode === "login" && styles.tabOn]}>
          <Text style={[styles.tabText, mode === "login" && styles.tabTextOn]}>Kirish</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => setMode("register")} style={[styles.tab, mode === "register" && styles.tabOn]}>
          <Text style={[styles.tabText, mode === "register" && styles.tabTextOn]}>Ro'yxatdan o'tish</Text>
        </TouchableOpacity>
      </View>

      {mode === "register" && (
        <TextInput style={styles.input} placeholder="Ismingiz" placeholderTextColor={colors.textFaint} value={ism} onChangeText={setIsm} />
      )}
      <TextInput
        style={styles.input} placeholderTextColor={colors.textFaint} placeholder="Email" autoCapitalize="none" keyboardType="email-address"
        value={email} onChangeText={setEmail}
      />
      <TextInput
        style={styles.input} placeholderTextColor={colors.textFaint} placeholder="Parol" secureTextEntry value={parol} onChangeText={setParol}
      />

      <TouchableOpacity style={styles.primary} onPress={submitEmail} disabled={busy}>
        <Text style={styles.primaryText}>
          {busy ? "..." : mode === "register" ? "Ro'yxatdan o'tish" : "Kirish"}
        </Text>
      </TouchableOpacity>

      {mode === "login" && (
        <TouchableOpacity onPress={forgot}>
          <Text style={styles.forgot}>Parolni unutdingizmi?</Text>
        </TouchableOpacity>
      )}

      <View style={styles.orRow}>
        <View style={styles.line} /><Text style={styles.or}>yoki</Text><View style={styles.line} />
      </View>

      <TouchableOpacity style={styles.social} onPress={() => socialSoon("Google")}>
        <Text style={styles.socialText}>  Google bilan kirish</Text>
      </TouchableOpacity>
      {Platform.OS === "ios" && (
        <TouchableOpacity style={[styles.social, styles.apple]} onPress={() => socialSoon("Apple")}>
          <Text style={[styles.socialText, { color: "#fff" }]}>  Apple bilan kirish</Text>
        </TouchableOpacity>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, backgroundColor: colors.bgSoft, padding: spacing.xl, justifyContent: "center" },
  logoImg: { width: 88, height: 88, borderRadius: radius.xl, alignSelf: "center", marginBottom: spacing.md },
  logo: { fontSize: 32, fontWeight: "900", color: colors.brand, textAlign: "center", letterSpacing: 2 },
  sub: { textAlign: "center", color: colors.textMuted, marginBottom: spacing.xl, fontSize: font.small },
  tabs: { flexDirection: "row", backgroundColor: colors.secondaryBg, borderRadius: radius.md, padding: 4, marginBottom: spacing.lg },
  tab: { flex: 1, paddingVertical: 10, alignItems: "center", borderRadius: radius.sm },
  tabOn: { backgroundColor: colors.bg },
  tabText: { color: colors.textMuted, fontWeight: "700" },
  tabTextOn: { color: colors.brand },
  input: {
    backgroundColor: colors.bg, borderRadius: radius.md, paddingHorizontal: 16,
    height: 52, fontSize: font.body, marginBottom: spacing.md, color: colors.text,
    ...shadow.sm,
  },
  primary: { backgroundColor: colors.brand, borderRadius: radius.md, paddingVertical: 16, alignItems: "center", marginTop: 4, ...shadow.md },
  primaryText: { color: "#fff", fontWeight: "800", fontSize: 15 },
  forgot: { color: colors.brand, textAlign: "center", marginTop: spacing.md, fontWeight: "600" },
  orRow: { flexDirection: "row", alignItems: "center", marginVertical: spacing.lg, gap: 10 },
  line: { flex: 1, height: 1, backgroundColor: colors.line },
  or: { color: colors.textMuted },
  social: {
    backgroundColor: colors.bg, borderRadius: radius.md, paddingVertical: 15,
    alignItems: "center", marginBottom: spacing.md, ...shadow.sm,
  },
  apple: { backgroundColor: "#000", borderColor: "#000" },
  socialText: { fontWeight: "700", color: colors.text },
});
