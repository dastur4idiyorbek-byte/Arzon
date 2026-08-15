import React from "react";
import { View, Text, StyleSheet, ScrollView } from "react-native";
import { colors, font, radius, spacing } from "../theme";

/**
 * Katalog — 3-bosqichда backend'дан (/api/products) mahsulotlar yuklanadi.
 * Hozir (1-bosqich) — asos/ko'rinish.
 */
export default function CatalogScreen() {
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.logo}>ARZON</Text>
        <View style={styles.balancePill}>
          <Text style={styles.balanceText}>🪙 0</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.body}>
        <View style={styles.banner}>
          <Text style={styles.bannerTitle}>ARZON — arzon narxlar</Text>
          <Text style={styles.bannerSub}>Har kuni yangi takliflar</Text>
        </View>

        <View style={styles.placeholder}>
          <Text style={styles.phIcon}>🛍️</Text>
          <Text style={styles.phTitle}>Katalog tayyorlanmoqda</Text>
          <Text style={styles.phSub}>
            3-bosqichда mahsulotlar backend'дан yuklanadi (qidiruv, filtr,
            savat, checkout).
          </Text>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  logo: { fontSize: font.h1, fontWeight: "800", color: colors.brand, letterSpacing: 1 },
  balancePill: {
    backgroundColor: "rgba(201,151,26,0.14)",
    borderColor: "rgba(201,151,26,0.35)",
    borderWidth: 1,
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  balanceText: { color: colors.gold, fontWeight: "800" },
  body: { padding: spacing.lg },
  banner: {
    backgroundColor: colors.brand,
    borderRadius: radius.md,
    padding: spacing.lg,
    marginBottom: spacing.lg,
  },
  bannerTitle: { color: "#fff", fontSize: 17, fontWeight: "800" },
  bannerSub: { color: "#fff", opacity: 0.92, marginTop: 4 },
  placeholder: { alignItems: "center", paddingVertical: 48, gap: 10 },
  phIcon: { fontSize: 52 },
  phTitle: { fontSize: font.h2, fontWeight: "700", color: colors.text },
  phSub: {
    fontSize: font.body,
    color: colors.textMuted,
    textAlign: "center",
    maxWidth: 300,
    lineHeight: 20,
  },
});
