/**
 * Ro'yxatdan tanlash oynasi — BARCHA variantlarni ko'rsatadi.
 *
 * NEGA KERAK: Android'dagi `Alert.alert` FAQAT 3 ta tugmani chizadi va
 * qolganini jimgina tashlab yuboradi. Shu sabab 4-variant ("Kripto hamyon")
 * ekranда umuman ko'rinmasdi. Bu oyna esa nechta variant bo'lsa hammasini
 * ko'rsatadi — ikonkasi va izohi bilan.
 *
 * Ishlatish:
 *   const choose = useChooser();
 *   const key = await choose({ title: "Turini tanlang", items: [...] });
 *   if (key !== null) { ... }   // null = bekor qilindi
 */
import React, { createContext, useContext, useRef, useState, useCallback } from "react";
import { View, Text, Modal, ScrollView, TouchableOpacity, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors, radius, spacing, font, border } from "../theme";

export type ChooserItem = {
  key: string;
  label: string;
  izoh?: string;
  icon?: keyof typeof Ionicons.glyphMap;
  rang?: string;
};

export type ChooserOptions = {
  title: string;
  message?: string;
  items: ChooserItem[];
};

type ChooserFn = (opts: ChooserOptions) => Promise<string | null>;

const Ctx = createContext<ChooserFn>(async () => null);
export const useChooser = (): ChooserFn => useContext(Ctx);

export function ChooserProvider({ children }: { children: React.ReactNode }) {
  const [opts, setOpts] = useState<ChooserOptions | null>(null);
  const resolver = useRef<((v: string | null) => void) | null>(null);

  const choose = useCallback<ChooserFn>((o) => {
    setOpts(o);
    return new Promise<string | null>((resolve) => {
      resolver.current = resolve;
    });
  }, []);

  function finish(result: string | null) {
    setOpts(null);
    resolver.current?.(result);
    resolver.current = null;
  }

  return (
    <Ctx.Provider value={choose}>
      {children}
      <Modal visible={!!opts} transparent animationType="fade" onRequestClose={() => finish(null)}>
        <View style={styles.backdrop}>
          <View style={styles.box}>
            <Text style={styles.title}>{opts?.title}</Text>
            {!!opts?.message && <Text style={styles.message}>{opts.message}</Text>}

            <ScrollView style={styles.list} contentContainerStyle={{ gap: 8 }}>
              {(opts?.items || []).map((it) => (
                <TouchableOpacity
                  key={it.key}
                  style={styles.item}
                  activeOpacity={0.8}
                  onPress={() => finish(it.key)}
                >
                  {!!it.icon && (
                    <View style={[styles.ikon, { backgroundColor: (it.rang || colors.brand) + "1A" }]}>
                      <Ionicons name={it.icon} size={20} color={it.rang || colors.brand} />
                    </View>
                  )}
                  <View style={{ flex: 1 }}>
                    <Text style={styles.itemLabel}>{it.label}</Text>
                    {!!it.izoh && <Text style={styles.itemIzoh}>{it.izoh}</Text>}
                  </View>
                  <Ionicons name="chevron-forward" size={18} color={colors.textFaint} />
                </TouchableOpacity>
              ))}
            </ScrollView>

            <TouchableOpacity style={styles.cancel} onPress={() => finish(null)}>
              <Text style={styles.cancelText}>Bekor</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </Ctx.Provider>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1, backgroundColor: "rgba(0,0,0,0.45)",
    alignItems: "center", justifyContent: "center", padding: spacing.lg,
  },
  box: {
    width: "100%", maxWidth: 420, maxHeight: "80%", backgroundColor: colors.bg,
    borderRadius: radius.lg, padding: spacing.xl, gap: 10,
  },
  title: { fontSize: font.h2, fontWeight: "800", color: colors.text },
  message: { color: colors.textMuted, fontSize: font.small, lineHeight: 19 },
  list: { flexGrow: 0, marginTop: 4 },
  item: {
    flexDirection: "row", alignItems: "center", gap: 12,
    borderRadius: radius.md, padding: 14, backgroundColor: colors.bg, ...border.hair,
  },
  ikon: { width: 38, height: 38, borderRadius: radius.sm, alignItems: "center", justifyContent: "center" },
  itemLabel: { fontWeight: "800", color: colors.text, fontSize: font.body },
  itemIzoh: { color: colors.textMuted, fontSize: font.tiny, marginTop: 2 },
  cancel: { borderRadius: radius.md, paddingVertical: 13, alignItems: "center", backgroundColor: colors.secondaryBg },
  cancelText: { fontWeight: "800", fontSize: font.small, color: colors.textMuted },
});

export default ChooserProvider;
