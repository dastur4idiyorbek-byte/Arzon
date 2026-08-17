/**
 * Panel bosh sahifasi — Admin panelidagi kabi kartochkali menyu.
 *
 * Nega: gorizontal bo'limlar (segment) tor ekranda tushunarsiz edi — yorliqlar
 * kesilib, qaysi bo'limda ekaningiz bilinmasdi. Kartochkali menyu esa har bir
 * bo'limni ikonka, nom va qisqa izoh bilan ko'rsatadi.
 */
import React from "react";
import { View, Text, StyleSheet, TouchableOpacity, ScrollView } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors, radius, spacing, font, shadow , border } from "../../theme";

export type PanelBolim = {
  key: string;
  label: string;
  izoh: string;
  icon: keyof typeof Ionicons.glyphMap;
  rang: string;
  /** O'ng tomonda ko'rsatiladigan son (masalan kutilayotgan so'rovlar). */
  son?: number;
};

export function PanelHome({
  sarlavha,
  izoh,
  bolimlar,
  onSelect,
}: {
  sarlavha: string;
  izoh?: string;
  bolimlar: PanelBolim[];
  onSelect: (key: string) => void;
}) {
  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.bgSoft }}
      contentContainerStyle={{ padding: spacing.lg, paddingBottom: spacing.xxl }}
    >
      <Text style={styles.sarlavha}>{sarlavha}</Text>
      {!!izoh && <Text style={styles.izoh}>{izoh}</Text>}

      <View style={{ gap: spacing.md, marginTop: spacing.lg }}>
        {bolimlar.map((b) => (
          <TouchableOpacity
            key={b.key}
            style={styles.karta}
            activeOpacity={0.85}
            onPress={() => onSelect(b.key)}
          >
            <View style={[styles.ikonka, { backgroundColor: b.rang + "1A" }]}>
              <Ionicons name={b.icon} size={24} color={b.rang} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.nomi}>{b.label}</Text>
              <Text style={styles.kartaIzoh}>{b.izoh}</Text>
            </View>
            {!!b.son && (
              <View style={styles.son}>
                <Text style={styles.sonText}>{b.son}</Text>
              </View>
            )}
            <Ionicons name="chevron-forward" size={20} color={colors.textFaint} />
          </TouchableOpacity>
        ))}
      </View>
    </ScrollView>
  );
}

/** Bo'lim ichidagi sahifa uchun sarlavha + orqaga tugmasi. */
export function BolimSarlavha({
  matn,
  onBack,
}: {
  matn: string;
  onBack: () => void;
}) {
  return (
    <View style={styles.bolimHead}>
      <TouchableOpacity onPress={onBack} style={styles.orqaga} hitSlop={8}>
        <Ionicons name="arrow-back" size={22} color={colors.brand} />
      </TouchableOpacity>
      <Text style={styles.bolimMatn}>{matn}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  sarlavha: { fontSize: font.h1, fontWeight: "900", color: colors.text },
  izoh: { color: colors.textMuted, marginTop: 4, lineHeight: 20 },
  karta: {
    flexDirection: "row", alignItems: "center", gap: 14,
    backgroundColor: colors.bg, borderRadius: radius.lg, padding: spacing.lg,
    ...border.hair,
  },
  ikonka: {
    width: 48, height: 48, borderRadius: radius.md,
    alignItems: "center", justifyContent: "center",
  },
  nomi: { fontWeight: "800", color: colors.text, fontSize: font.h3 },
  kartaIzoh: { color: colors.textMuted, fontSize: font.small, marginTop: 2 },
  son: {
    minWidth: 26, height: 26, borderRadius: 13, backgroundColor: colors.sale,
    alignItems: "center", justifyContent: "center", paddingHorizontal: 7,
  },
  sonText: { color: "#fff", fontWeight: "800", fontSize: font.small },

  bolimHead: {
    flexDirection: "row", alignItems: "center", gap: 12,
    paddingHorizontal: spacing.lg, paddingVertical: spacing.md,
    backgroundColor: colors.bg, borderBottomWidth: 1, borderBottomColor: colors.line,
  },
  orqaga: {
    width: 36, height: 36, borderRadius: radius.sm, backgroundColor: colors.brandSoft,
    alignItems: "center", justifyContent: "center",
  },
  bolimMatn: { fontWeight: "800", color: colors.text, fontSize: font.h2 },
});
