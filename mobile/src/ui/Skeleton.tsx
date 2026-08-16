/**
 * Skeleton — yuklanish paytida kontent SHAKLINI ko'rsatadi.
 *
 * NEGA SPINNER EMAS (2026 me'yori): aylanuvchi belgi "ilova qotib qoldi"
 * hissini beradi va ekranni bo'shatib qo'yadi. Skeleton esa nima kelishini
 * oldindan ko'rsatadi — kutish qisqaroq tuyuladi va ekran "sakramaydi",
 * chunki joylashuv allaqachon o'z o'rnida turadi.
 */
import React, { useEffect, useRef } from "react";
import { View, StyleSheet, Animated, ViewStyle } from "react-native";
import { colors, radius, spacing, shadow } from "../theme";

/** Bitta kulrang blok — sekin "nafas oladi". */
export function SkeletonBlock({
  w,
  h,
  r = radius.xs,
  style,
}: {
  w?: number | string;
  h: number;
  r?: number;
  style?: ViewStyle;
}) {
  const puls = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(puls, { toValue: 1, duration: 700, useNativeDriver: true }),
        Animated.timing(puls, { toValue: 0, duration: 700, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [puls]);

  return (
    <Animated.View
      style={[
        {
          width: (w as any) ?? "100%",
          height: h,
          borderRadius: r,
          backgroundColor: colors.skeleton,
          opacity: puls.interpolate({ inputRange: [0, 1], outputRange: [1, 0.45] }),
        },
        style,
      ]}
    />
  );
}

/** Katalog kartochkasi shakli. */
export function SkeletonProductCard() {
  return (
    <View style={styles.card}>
      <SkeletonBlock h={0} style={styles.rasm} />
      <View style={{ padding: 12, gap: 8 }}>
        <SkeletonBlock w="45%" h={10} />
        <SkeletonBlock w="85%" h={13} />
        <SkeletonBlock w="55%" h={16} />
        <SkeletonBlock h={38} r={radius.sm} style={{ marginTop: 4 }} />
      </View>
    </View>
  );
}

/** Katalog to'ri (2 ustun). */
export function SkeletonCatalog({ soni = 6 }: { soni?: number }) {
  const qatorlar = Math.ceil(soni / 2);
  return (
    <View style={{ paddingHorizontal: spacing.lg, gap: spacing.md }}>
      {Array.from({ length: qatorlar }).map((_, i) => (
        <View key={i} style={{ flexDirection: "row", gap: spacing.md }}>
          <View style={{ flex: 1 }}><SkeletonProductCard /></View>
          <View style={{ flex: 1 }}><SkeletonProductCard /></View>
        </View>
      ))}
    </View>
  );
}

/** Ro'yxat (buyurtma, so'rov, panel elementlari) shakli. */
export function SkeletonList({ soni = 4, balandlik = 96 }: { soni?: number; balandlik?: number }) {
  return (
    <View style={{ padding: spacing.lg, gap: spacing.md }}>
      {Array.from({ length: soni }).map((_, i) => (
        <View key={i} style={styles.qator}>
          <SkeletonBlock w={48} h={48} r={radius.sm} />
          <View style={{ flex: 1, gap: 8 }}>
            <SkeletonBlock w="60%" h={13} />
            <SkeletonBlock w="35%" h={11} />
            <SkeletonBlock w="80%" h={11} />
          </View>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.bg,
    borderRadius: radius.lg,
    overflow: "hidden",
    ...shadow.sm,
  },
  rasm: { aspectRatio: 1, height: undefined, borderRadius: 0 },
  qator: {
    flexDirection: "row", alignItems: "center", gap: 12,
    backgroundColor: colors.bg, borderRadius: radius.lg,
    padding: spacing.lg, ...shadow.sm,
  },
});
