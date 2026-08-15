import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { colors, font } from "../theme";

/** Umumiy "tez orada" ekrani — bosqichlar to'ldirilgunча asos sifatida. */
export default function PlaceholderScreen({
  icon,
  title,
  sub,
}: {
  icon: string;
  title: string;
  sub: string;
}) {
  return (
    <View style={styles.container}>
      <Text style={styles.icon}>{icon}</Text>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.sub}>{sub}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
    gap: 10,
  },
  icon: { fontSize: 52 },
  title: { fontSize: font.h2, fontWeight: "700", color: colors.text },
  sub: {
    fontSize: font.body,
    color: colors.textMuted,
    textAlign: "center",
    maxWidth: 300,
    lineHeight: 20,
  },
});
