import React from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";
import { colors, font, radius } from "../theme";

/** Umumiy "tez orada" ekrani — bosqichlar to'ldirilgunча asos sifatida. */
export default function PlaceholderScreen({
  icon,
  title,
  sub,
  onPress,
  buttonLabel,
}: {
  icon: string;
  title: string;
  sub: string;
  onPress?: () => void;
  buttonLabel?: string;
}) {
  return (
    <View style={styles.container}>
      <Text style={styles.icon}>{icon}</Text>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.sub}>{sub}</Text>
      {onPress && buttonLabel && (
        <TouchableOpacity style={styles.btn} onPress={onPress}>
          <Text style={styles.btnText}>{buttonLabel}</Text>
        </TouchableOpacity>
      )}
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
  title: { fontSize: font.h2, fontWeight: "700", color: colors.text, textAlign: "center" },
  sub: {
    fontSize: font.body,
    color: colors.textMuted,
    textAlign: "center",
    maxWidth: 320,
    lineHeight: 20,
  },
  btn: {
    marginTop: 12,
    backgroundColor: colors.brand,
    borderRadius: radius.md,
    paddingVertical: 12,
    paddingHorizontal: 28,
  },
  btnText: { color: "#fff", fontWeight: "800" },
});
