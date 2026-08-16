/**
 * Panel ekranlari uchun umumiy UI bo'laklari (admin/moliya/menejer).
 * Rol-rang tizimiga mos, takrorlanishни kamaytiradi.
 */
import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  ScrollViewProps,
  ScrollView,
} from "react-native";
import { colors, radius, spacing, font, shadow } from "../../theme";
import { SkeletonList } from "../../ui/Skeleton";

export function Segmented({
  items,
  value,
  onChange,
}: {
  items: { key: string; label: string }[];
  value: string;
  onChange: (k: string) => void;
}) {
  // DIQQAT: gorizontal ScrollView'ni balandligi cheklangan View ichiga olamiz.
  // Aks holda u ota-konteynerdagi bo'sh joyni to'ldirib, tugmalar uzun ovalga
  // cho'zilib ketadi (RN'da gorizontal ScrollView shunday xatoga olib keladi).
  return (
    <View style={styles.segHost}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.segWrap}
      >
        {items.map((it) => {
          const active = it.key === value;
          return (
            <TouchableOpacity
              key={it.key}
              onPress={() => onChange(it.key)}
              style={[styles.seg, active && styles.segActive]}
            >
              <Text style={[styles.segText, active && styles.segTextActive]}>
                {it.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>
    </View>
  );
}

export function Card({ children, style }: any) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function Btn({
  label,
  onPress,
  tone = "brand",
  disabled,
  style,
}: {
  label: string;
  onPress: () => void;
  tone?: "brand" | "store" | "sale" | "gold" | "ghost";
  disabled?: boolean;
  style?: any;
}) {
  const bg =
    tone === "store"
      ? colors.store
      : tone === "sale"
      ? colors.sale
      : tone === "gold"
      ? colors.gold
      : tone === "ghost"
      ? "transparent"
      : colors.brand;
  const fg = tone === "ghost" ? colors.brand : "#fff";
  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled}
      style={[
        styles.btn,
        { backgroundColor: bg, opacity: disabled ? 0.5 : 1 },
        tone === "ghost" && { borderWidth: 1.5, borderColor: colors.brand },
        style,
      ]}
    >
      <Text style={[styles.btnText, { color: fg }]}>{label}</Text>
    </TouchableOpacity>
  );
}

export function Empty({ text }: { text: string }) {
  return <Text style={styles.empty}>{text}</Text>;
}

/** Yuklanish holati — SKELETON (spinner emas).
 *
 * 2026 me'yori: aylanuvchi belgi "qotib qoldi" hissini beradi. Skeleton esa
 * kontent shaklini oldindan ko'rsatadi — kutish qisqaroq tuyuladi va
 * ma'lumot kelganda joylashuv sakramaydi. */
export function Loader() {
  return (
    <View style={{ flex: 1, backgroundColor: colors.bgSoft }}>
      <SkeletonList soni={4} />
    </View>
  );
}

export function Screen(props: ScrollViewProps) {
  return (
    <ScrollView
      style={{ backgroundColor: colors.bg }}
      contentContainerStyle={{ padding: spacing.lg, paddingBottom: 40 }}
      {...props}
    />
  );
}

export function Field({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.fieldRow}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <Text style={styles.fieldValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  // Balandligi qat'iy — tugmalar cho'zilib ketmasligi uchun.
  segHost: { height: 56, flexGrow: 0, flexShrink: 0, backgroundColor: colors.bg },
  segWrap: { paddingHorizontal: spacing.lg, paddingVertical: spacing.sm, gap: 8, alignItems: "center" },
  seg: {
    height: 38,
    justifyContent: "center",
    paddingHorizontal: 16,
    borderRadius: 999,
    backgroundColor: colors.secondaryBg,
  },
  segActive: { backgroundColor: colors.brand },
  segText: { color: colors.textMuted, fontWeight: "700", fontSize: 13 },
  segTextActive: { color: "#fff" },
  card: {
    backgroundColor: colors.bg,
    borderRadius: radius.lg,
    padding: 16,
    marginBottom: 12,
    ...shadow.sm,
  },
  btn: {
    borderRadius: radius.sm,
    height: 46,
    justifyContent: "center",
    paddingHorizontal: 16,
    alignItems: "center",
  },
  btnText: { fontWeight: "800", fontSize: 14 },
  empty: { textAlign: "center", color: colors.textMuted, marginTop: 40 },
  fieldRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 4,
  },
  fieldLabel: { color: colors.textMuted },
  fieldValue: { color: colors.text, fontWeight: "700" },
});
