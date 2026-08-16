/**
 * Matn so'rash oynasi — BARCHA platformada ishlaydi.
 *
 * NEGA KERAK: React Native'ning `Alert.prompt` funksiyasi FAQAT iOS'da bor.
 * Android'da u `undefined` — shuning uchun unga tayangan tugmalar (admin
 * qo'shish, sabab bilan rad etish, kuryer telefoni...) Android'da umuman
 * ishlamasdi. Bu modul o'z oynasini chizadi, demak hamma joyda bir xil.
 *
 * Ishlatish:
 *   const prompt = usePrompt();
 *   const qiymat = await prompt({ title: "Sabab", message: "..." });
 *   if (qiymat !== null) { ... }   // null = foydalanuvchi bekor qildi
 */
import React, { createContext, useContext, useRef, useState, useCallback } from "react";
import {
  View, Text, Modal, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform,
} from "react-native";
import { colors, radius, spacing, font } from "../theme";

export type PromptOptions = {
  title: string;
  message?: string;
  placeholder?: string;
  defaultValue?: string;
  keyboardType?: "default" | "numeric" | "email-address" | "phone-pad";
  submitLabel?: string;
  multiline?: boolean;
};

type PromptFn = (opts: PromptOptions) => Promise<string | null>;

const Ctx = createContext<PromptFn>(async () => null);
export const usePrompt = (): PromptFn => useContext(Ctx);

export function PromptProvider({ children }: { children: React.ReactNode }) {
  const [opts, setOpts] = useState<PromptOptions | null>(null);
  const [value, setValue] = useState("");
  const resolver = useRef<((v: string | null) => void) | null>(null);

  const prompt = useCallback<PromptFn>((o) => {
    setOpts(o);
    setValue(o.defaultValue ?? "");
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
    <Ctx.Provider value={prompt}>
      {children}
      <Modal visible={!!opts} transparent animationType="fade" onRequestClose={() => finish(null)}>
        <KeyboardAvoidingView
          style={styles.backdrop}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
        >
          <View style={styles.box}>
            <Text style={styles.title}>{opts?.title}</Text>
            {!!opts?.message && <Text style={styles.message}>{opts.message}</Text>}
            <TextInput
              style={[styles.input, opts?.multiline && styles.inputMulti]}
              value={value}
              onChangeText={setValue}
              placeholder={opts?.placeholder}
              placeholderTextColor={colors.textMuted}
              keyboardType={opts?.keyboardType || "default"}
              autoCapitalize="none"
              autoFocus
              multiline={opts?.multiline}
              onSubmitEditing={() => !opts?.multiline && finish(value)}
            />
            <View style={styles.row}>
              <TouchableOpacity style={[styles.btn, styles.cancel]} onPress={() => finish(null)}>
                <Text style={[styles.btnText, { color: colors.textMuted }]}>Bekor</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.btn, styles.ok]} onPress={() => finish(value)}>
                <Text style={[styles.btnText, { color: "#fff" }]}>
                  {opts?.submitLabel || "Tasdiqlash"}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
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
    width: "100%", maxWidth: 420, backgroundColor: colors.bg,
    borderRadius: radius.lg, padding: spacing.xl, gap: 10,
  },
  title: { fontSize: font.h2, fontWeight: "800", color: colors.text },
  message: { color: colors.textMuted, fontSize: 13, lineHeight: 19 },
  input: {
    borderWidth: 1, borderColor: colors.line, backgroundColor: colors.secondaryBg,
    borderRadius: radius.sm, padding: 12, color: colors.text, fontSize: 15,
  },
  inputMulti: { height: 90, textAlignVertical: "top" },
  row: { flexDirection: "row", gap: 10, marginTop: 4 },
  btn: { flex: 1, borderRadius: radius.md, paddingVertical: 13, alignItems: "center" },
  cancel: { backgroundColor: colors.secondaryBg },
  ok: { backgroundColor: colors.brand },
  btnText: { fontWeight: "800", fontSize: 14 },
});
