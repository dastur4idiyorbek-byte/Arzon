/**
 * Butun ilova uchun xavfsizlik to'ri.
 *
 * Biror ekranda kutilmagan xato chiqsa React daraxti butunlay o'chadi va
 * foydalanuvchi FAQAT oq ekran ko'radi ("ilova ochilmayapti"). Bu komponent
 * xatoni ushlab qoladi, tushunarli xabar va "Qayta urinish" tugmasini
 * ko'rsatadi — hamda xato matnini beradi, shunda muammoni aytish oson bo'ladi.
 */
import React from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from "react-native";
import * as Updates from "expo-updates";
import { colors, radius, spacing, font, border } from "../theme";

type Props = { children: React.ReactNode };
type State = { xato: Error | null };

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { xato: null };

  static getDerivedStateFromError(xato: Error): State {
    return { xato };
  }

  async qaytaIshga() {
    // Ilovani to'liq qayta yuklaymiz (yangilanish bo'lsa u ham qo'llanadi).
    try {
      await Updates.reloadAsync();
    } catch {
      this.setState({ xato: null });
    }
  }

  render() {
    const { xato } = this.state;
    if (!xato) return this.props.children;
    return (
      <ScrollView style={styles.host} contentContainerStyle={styles.wrap}>
        <Text style={styles.emoji}>😕</Text>
        <Text style={styles.sarlavha}>Ilovada xatolik yuz berdi</Text>
        <Text style={styles.izoh}>
          Kechirasiz. "Qayta urinish"ni bosing — ko'p hollarda shu yetarli bo'ladi.
        </Text>
        <TouchableOpacity style={styles.btn} onPress={() => this.qaytaIshga()} activeOpacity={0.85}>
          <Text style={styles.btnText}>Qayta urinish</Text>
        </TouchableOpacity>
        <View style={styles.detal}>
          <Text style={styles.detalLabel}>Texnik ma'lumot (dasturchi uchun):</Text>
          <Text style={styles.detalText} selectable>
            {xato?.message || String(xato)}
          </Text>
        </View>
      </ScrollView>
    );
  }
}

const styles = StyleSheet.create({
  host: { flex: 1, backgroundColor: colors.bgSoft },
  wrap: { flexGrow: 1, justifyContent: "center", padding: spacing.xl, gap: 10 },
  emoji: { fontSize: 52, textAlign: "center" },
  sarlavha: { fontSize: font.h1, fontWeight: "900", color: colors.text, textAlign: "center" },
  izoh: { color: colors.textMuted, textAlign: "center", lineHeight: 21 },
  btn: {
    backgroundColor: colors.brand, borderRadius: radius.md,
    paddingVertical: 16, alignItems: "center", marginTop: spacing.md,
  },
  btnText: { color: "#fff", fontWeight: "800", fontSize: font.body + 1 },
  detal: {
    marginTop: spacing.xl, backgroundColor: colors.bg,
    borderRadius: radius.md, padding: spacing.md, gap: 6, ...border.hair,
  },
  detalLabel: { color: colors.textFaint, fontSize: font.tiny },
  detalText: { color: colors.sale, fontSize: font.tiny, lineHeight: 17 },
});

export default ErrorBoundary;
