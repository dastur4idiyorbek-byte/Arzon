/**
 * Moliya — to'lov usullarini boshqarish (4.2).
 *
 * Mijoz buyurtma to'lovini shu usullar orqali amalga oshiradi
 * (OrderPaymentScreen). Bu yerda ular qo'shiladi, tahrirlanadi,
 * yoqiladi/o'chiriladi va o'chirib tashlanadi.
 *
 * Backend: /api/moliya/tolov-usullari (GET, POST, PATCH, toggle, DELETE).
 */
import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Alert, Switch } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { Ionicons } from "@expo/vector-icons";
import { api } from "../../api";
import { colors, radius, spacing, font, shadow } from "../../theme";
import { Screen, Card, Btn, Loader, Empty } from "./PanelUI";
import { usePrompt } from "../../ui/Prompt";
import { useChooser } from "../../ui/Chooser";

type Usul = {
  id: number; turi: string; nomi: string; qiymat: string | null;
  egasi: string | null; izoh: string | null; faol: boolean;
};

const TURLAR: {
  key: string; label: string; icon: keyof typeof Ionicons.glyphMap;
  izoh: string; rang: string;
}[] = [
  { key: "karta", label: "Bank kartasi", icon: "card-outline",
    izoh: "Optima, MBank, Demir va h.k.", rang: colors.brand },
  { key: "telefon", label: "Telefon raqami", icon: "phone-portrait-outline",
    izoh: "Balans orqali o'tkazma", rang: colors.store },
  { key: "qr_kod", label: "QR kod", icon: "qr-code-outline",
    izoh: "Mijoz QR kodni skanerlaydi", rang: colors.info },
  { key: "crypto", label: "Kripto hamyon", icon: "logo-bitcoin",
    izoh: "USDT, BTC va boshqa hamyonlar", rang: colors.gold },
];

type Hisob = { karta_raqami: string; hisob_egasi: string } | null;

export default function TolovUsullariScreen() {
  const [rows, setRows] = useState<Usul[]>([]);
  const [hisob, setHisob] = useState<Hisob>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const prompt = usePrompt();
  const choose = useChooser();

  const load = useCallback(async () => {
    const [u, h] = await Promise.all([
      api<Usul[]>("/api/moliya/tolov-usullari"),
      api<Hisob>("/api/moliya/platforma-hisob"),
    ]);
    setRows(u.ok && Array.isArray(u.data) ? u.data : []);
    setHisob(h.ok ? (h.data as Hisob) : null);
    setLoading(false);
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  /** Platforma hisobi — do'kon ochish/arenda to'lovlari shu kartaga tushadi. */
  async function hisobniOzgartir() {
    const karta = await prompt({
      title: "Platforma kartasi",
      message: "Do'kon ochish va arenda to'lovlari shu kartaga tushadi:",
      defaultValue: hisob?.karta_raqami || "",
      placeholder: "8600 ...",
      submitLabel: "Keyingisi",
    });
    if (karta === null || karta.trim().length < 4) return;
    const egasi = await prompt({
      title: "Hisob egasi",
      message: "Karta egasining ism-familiyasi:",
      defaultValue: hisob?.hisob_egasi || "",
      submitLabel: "Saqlash",
    });
    if (egasi === null || !egasi.trim()) return;
    await soraw("/api/moliya/platforma-hisob", "POST",
      { karta_raqami: karta.trim(), hisob_egasi: egasi.trim() }, "Platforma hisobi saqlandi");
  }

  async function soraw(path: string, method: string, body?: any, ok_matn = "Bajarildi") {
    setBusy(true);
    const { ok, status, data } = await api(path, { method, body });
    setBusy(false);
    if (ok) {
      Alert.alert("✅ " + ok_matn, "");
      load();
      return true;
    }
    Alert.alert("Xatolik", (data as any)?.detail ||
      (status === 0 ? "Internet yo'q yoki server javob bermadi." : `Xato kodi: ${status}`));
    return false;
  }

  /** Yangi usul qo'shish — turi tanlanadi, so'ng nomi va raqami so'raladi.
   *
   * DIQQAT: bu yerda Alert.alert ISHLATILMAYDI — Android'da u faqat 3 ta
   * tugmani chizadi va qolganini (masalan "Kripto hamyon") yashirib qo'yadi. */
  async function yangi() {
    const turi = await choose({
      title: "Qanday to'lov usuli?",
      message: "Mijoz buyurtma pulini shu usul orqali o'tkazadi.",
      items: TURLAR,
    });
    if (turi === null) return;
    const t = TURLAR.find((x) => x.key === turi);
    yangiDavom(turi, t?.label || turi);
  }

  async function yangiDavom(turi: string, turLabel: string) {
    const nomi = await prompt({
      title: "Nomi",
      message: `Mijoz shu nomni ko'radi (masalan: "Optima Bank", "MBank").`,
      placeholder: turLabel,
      submitLabel: "Keyingisi",
    });
    if (nomi === null || !nomi.trim()) return;

    // Har tur uchun so'raladigan qiymat boshqacha bo'ladi.
    const q: Record<string, { title: string; message: string; placeholder: string }> = {
      telefon: {
        title: "Telefon raqami", message: "Mijoz shu raqamga pul o'tkazadi:",
        placeholder: "+996 ...",
      },
      crypto: {
        title: "Hamyon manzili",
        message: "Manzilni TARMOG'I bilan yozing — noto'g'ri tarmoqqa yuborilgan pul yo'qoladi.",
        placeholder: "USDT (TRC20): TXxxxxx...",
      },
      qr_kod: {
        title: "QR kod ma'lumoti", message: "QR kod ichidagi manzil yoki raqam:",
        placeholder: "https://... yoki 8600 ...",
      },
      karta: {
        title: "Karta raqami", message: "Mijoz shu kartaga pul o'tkazadi:",
        placeholder: "8600 ...",
      },
    };
    const s = q[turi] || q.karta;

    const qiymat = await prompt({
      title: s.title,
      message: s.message,
      placeholder: s.placeholder,
      keyboardType: turi === "telefon" ? "phone-pad" : "default",
      submitLabel: "Keyingisi",
    });
    if (qiymat === null || !qiymat.trim()) return;

    const egasi = await prompt({
      title: turi === "crypto" ? "Tarmoq yoki izoh" : "Hisob egasi",
      message: turi === "crypto"
        ? "Masalan: USDT TRC20 (bo'sh qoldirsangiz ham bo'ladi):"
        : "Ism-familiya (bo'sh qoldirsangiz ham bo'ladi):",
      placeholder: turi === "crypto" ? "USDT TRC20" : "Masalan: Diyorbek A.",
      submitLabel: "Qo'shish",
    });
    if (egasi === null) return;

    await soraw("/api/moliya/tolov-usullari", "POST", {
      turi, nomi: nomi.trim(), qiymat: qiymat.trim(),
      egasi: egasi.trim() || null,
    }, "To'lov usuli qo'shildi");
  }

  async function tahrir(u: Usul) {
    const qiymat = await prompt({
      title: "Raqamni o'zgartirish",
      message: `"${u.nomi}" uchun yangi raqam:`,
      defaultValue: u.qiymat || "",
      submitLabel: "Saqlash",
    });
    if (qiymat === null || !qiymat.trim()) return;
    await soraw(`/api/moliya/tolov-usullari/${u.id}`, "PATCH",
      { qiymat: qiymat.trim() }, "Yangilandi");
  }

  function ochir(u: Usul) {
    Alert.alert("O'chirish", `"${u.nomi}" usulini o'chirasizmi?`, [
      { text: "Yo'q" },
      {
        text: "Ha, o'chir", style: "destructive",
        onPress: () => soraw(`/api/moliya/tolov-usullari/${u.id}`, "DELETE", undefined, "O'chirildi"),
      },
    ]);
  }

  if (loading) return <Loader />;

  return (
    <Screen>
      {/* Platforma hisobi — do'kon ochish/arenda to'lovlari uchun */}
      <Card style={{ backgroundColor: colors.goldSoft }}>
        <View style={styles.head}>
          <Ionicons name="business-outline" size={20} color={colors.gold} />
          <View style={{ flex: 1 }}>
            <Text style={styles.nomi}>Platforma hisobi</Text>
            <Text style={styles.tur}>Do'kon ochish va arenda to'lovlari</Text>
          </View>
        </View>
        <Text style={styles.qiymat}>{hisob?.karta_raqami || "sozlanmagan"}</Text>
        {!!hisob?.hisob_egasi && <Text style={styles.egasi}>👤 {hisob.hisob_egasi}</Text>}
        <Btn label={hisob ? "✏️ O'zgartirish" : "➕ Sozlash"} tone="gold" disabled={busy}
          style={{ marginTop: 12 }} onPress={hisobniOzgartir} />
      </Card>

      <Text style={styles.bolim}>Buyurtma to'lovi usullari</Text>
      <Text style={styles.izoh}>
        Mijozlar buyurtma pulini shu usullar orqali o'tkazadi (karta, bank, kripto).
        Faqat <Text style={{ fontWeight: "800" }}>yoqilgan</Text> usullar ilovada ko'rinadi.
      </Text>

      {rows.length === 0 ? (
        <Empty text="Hali to'lov usuli qo'shilmagan." />
      ) : (
        rows.map((u) => {
          const tur = TURLAR.find((t) => t.key === u.turi);
          return (
            <Card key={u.id} style={!u.faol && styles.ochiq}>
              <View style={styles.head}>
                <Ionicons name={tur?.icon || "wallet-outline"} size={20} color={colors.brand} />
                <View style={{ flex: 1 }}>
                  <Text style={styles.nomi}>{u.nomi}</Text>
                  <Text style={styles.tur}>{tur?.label || u.turi}</Text>
                </View>
                <Switch
                  value={!!u.faol}
                  disabled={busy}
                  onValueChange={() => {
                    soraw(`/api/moliya/tolov-usullari/${u.id}/toggle`, "POST", undefined,
                      u.faol ? "O'chirildi" : "Yoqildi");
                  }}
                  trackColor={{ true: colors.store, false: colors.line }}
                  thumbColor="#fff"
                />
              </View>

              <Text style={styles.qiymat}>{u.qiymat || "—"}</Text>
              {!!u.egasi && <Text style={styles.egasi}>👤 {u.egasi}</Text>}

              <View style={styles.amallar}>
                <Btn label="✏️ Tahrirlash" tone="ghost" disabled={busy}
                  style={{ flex: 1 }} onPress={() => tahrir(u)} />
                <Btn label="🗑 O'chirish" tone="sale" disabled={busy}
                  style={{ flex: 1 }} onPress={() => ochir(u)} />
              </View>
            </Card>
          );
        })
      )}

      <Btn label="➕ Yangi to'lov usuli" onPress={yangi} disabled={busy}
        style={{ marginTop: spacing.md }} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  bolim: { fontWeight: "900", color: colors.text, fontSize: font.h2, marginTop: spacing.lg },
  izoh: { color: colors.textMuted, fontSize: font.small, lineHeight: 19, marginTop: 4, marginBottom: spacing.md },
  ochiq: { opacity: 0.55 },
  head: { flexDirection: "row", alignItems: "center", gap: 10 },
  nomi: { fontWeight: "800", color: colors.text, fontSize: font.h3 },
  tur: { color: colors.textMuted, fontSize: font.tiny },
  qiymat: { fontSize: 18, fontWeight: "800", color: colors.text, letterSpacing: 1, marginTop: 10 },
  egasi: { color: colors.store, fontWeight: "600", fontSize: font.small, marginTop: 2 },
  amallar: { flexDirection: "row", gap: 8, marginTop: 12 },
});
