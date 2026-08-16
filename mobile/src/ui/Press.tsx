/**
 * Press — bosilganda biroz kichrayadigan bosiladigan yuza.
 *
 * NEGA: 2026 me'yorida harakat bezak emas, JAVOB. Barmoq tekkanda element
 * darhol javob bersa, ilova "tirik" tuyuladi; opacity o'zgarishi esa sezilmaydi.
 * Spring qaytishi tabiiy his beradi.
 */
import React, { useRef } from "react";
import { Animated, Pressable, ViewStyle, StyleProp } from "react-native";

export function Press({
  children,
  onPress,
  disabled,
  style,
  scale = 0.97,
}: {
  children: React.ReactNode;
  onPress?: () => void;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
  /** Bosilgandagi o'lcham (1 = o'zgarmaydi). Katta yuzaga 0.97, kichikka 0.93. */
  scale?: number;
}) {
  const s = useRef(new Animated.Value(1)).current;

  const bosildi = () =>
    Animated.spring(s, {
      toValue: scale,
      useNativeDriver: true,
      speed: 40,
      bounciness: 0,
    }).start();

  const qoyildi = () =>
    Animated.spring(s, {
      toValue: 1,
      useNativeDriver: true,
      speed: 30,
      bounciness: 8,
    }).start();

  return (
    <Pressable
      onPress={onPress}
      onPressIn={bosildi}
      onPressOut={qoyildi}
      disabled={disabled}
    >
      <Animated.View style={[style, { transform: [{ scale: s }] }]}>
        {children}
      </Animated.View>
    </Pressable>
  );
}
