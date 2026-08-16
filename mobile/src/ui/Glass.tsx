/**
 * Shisha (glass) yuzalar va chegirma taymeri.
 *
 * ESLATMA — HAQIQIY BLUR haqida ochiq gap: orqadagi kontentni chinakam
 * xiralashtirish uchun `expo-blur` (native kutubxona) kerak, u esa YANGI APK
 * talab qiladi. Shu sababli bu yerda blur "taqlid" qilinadi: yarim shaffof
 * oq qatlam + ingichka yorug' chegara + yumshoq soya. Amalda bu deyarli bir
 * xil taassurot beradi va yangilanish orqali darhol yetadi.
 */
import React, { useEffect, useState } from "react";
import { View, Text, StyleSheet, ViewStyle, StyleProp } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors, radius, spacing, font, shadow } from "../theme";

/** Yarim shaffof "shisha" yuza — kontent ustida suzadi. */
export function Glass({
  children,
  style,
  tone = "light",
}: {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  /** light — oq shisha (yorug' fonda), dark — qora shisha (rasm ustida). */
  tone?: "light" | "dark";
}) {
  return (
    <View
      style={[
        styles.glass,
        tone === "dark" ? styles.glassDark : styles.glassLight,
        style,
      ]}
    >
      {children}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Chegirma taymeri
// ---------------------------------------------------------------------------
function qolgan(muddat: string): { tugadi: boolean; matn: string } {
  const ms = new Date(muddat).getTime() - Date.now();
  if (isNaN(ms) || ms <= 0) return { tugadi: true, matn: "" };
  const kun = Math.floor(ms / 86400000);
  const soat = Math.floor((ms % 86400000) / 3600000);
  const daq = Math.floor((ms % 3600000) / 60000);
  const son = Math.floor((ms % 60000) / 1000);
  if (kun > 0) return { tugadi: false, matn: `${kun} kun ${soat} soat` };
  const ikki = (n: number) => String(n).padStart(2, "0");
  return { tugadi: false, matn: `${ikki(soat)}:${ikki(daq)}:${ikki(son)}` };
}

/**
 * Chegirma tugashiga qancha qolgani — har soniyada yangilanadi.
 * Shoshilish hissi savdoda konversiyani oshiradi (marketplace odati).
 */
export function ChegirmaTaymer({
  muddat,
  kichik,
}: {
  muddat?: string | null;
  kichik?: boolean;
}) {
  const [holat, setHolat] = useState(() => (muddat ? qolgan(muddat) : null));

  useEffect(() => {
    if (!muddat) return;
    setHolat(qolgan(muddat));
    const t = setInterval(() => setHolat(qolgan(muddat)), 1000);
    return () => clearInterval(t);
  }, [muddat]);

  if (!muddat || !holat || holat.tugadi) return null;

  return (
    <View style={[styles.taymer, kichik && styles.taymerKichik]}>
      <Ionicons name="time-outline" size={kichik ? 12 : 15} color={colors.sale} />
      <Text style={[styles.taymerText, kichik && styles.taymerTextKichik]}>
        {kichik ? holat.matn : `Chegirma tugashiga ${holat.matn}`}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  glass: {
    borderRadius: radius.lg,
    borderWidth: 1,
    overflow: "hidden",
    ...shadow.md,
  },
  glassLight: {
    backgroundColor: "rgba(255,255,255,0.82)",
    borderColor: "rgba(255,255,255,0.9)",
  },
  glassDark: {
    backgroundColor: "rgba(15,17,21,0.55)",
    borderColor: "rgba(255,255,255,0.18)",
  },

  taymer: {
    flexDirection: "row", alignItems: "center", gap: 6,
    backgroundColor: colors.saleSoft, borderRadius: radius.sm,
    paddingHorizontal: 12, paddingVertical: 9, alignSelf: "flex-start",
  },
  taymerKichik: {
    paddingHorizontal: 8, paddingVertical: 4, gap: 4,
    borderRadius: radius.xs,
  },
  taymerText: { color: colors.sale, fontWeight: "800", fontSize: font.small },
  taymerTextKichik: { fontSize: font.tiny },
});
