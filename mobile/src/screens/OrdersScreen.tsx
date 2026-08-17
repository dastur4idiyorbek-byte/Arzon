import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, FlatList, RefreshControl, TouchableOpacity, Linking } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { Ionicons } from "@expo/vector-icons";
import { api, money } from "../api";
import { colors, radius, spacing, font, shadow, tracking , border } from "../theme";
import { Order } from "../types";
import { Loader } from "./panels/PanelUI";

const HOLAT: Record<string, { t: string; c: string; bg: string; icon: keyof typeof Ionicons.glyphMap }> = {
  tolov_kutilmoqda: { t: "To'lov kutilmoqda", c: colors.gold, bg: "rgba(184,134,11,0.10)", icon: "wallet-outline" },
  yangi: { t: "Yangi", c: colors.info, bg: "#E8F1FA", icon: "sparkles-outline" },
  tayyorlanmoqda: { t: "Tayyorlanmoqda", c: colors.warn, bg: colors.brandSoft, icon: "cube-outline" },
  yolda: { t: "Yo'lda", c: colors.brand, bg: colors.brandSoft, icon: "bicycle-outline" },
  topshirildi: { t: "Topshirildi", c: colors.store, bg: colors.storeSoft, icon: "checkmark-circle-outline" },
  bekor_qilindi: { t: "Bekor qilindi", c: colors.sale, bg: colors.saleSoft, icon: "close-circle-outline" },
};

// Buyurtma qaysi bosqichda ekanini ko'rsatuvchi yo'lak.
const BOSQICH = ["yangi", "tayyorlanmoqda", "yolda", "topshirildi"];

export default function OrdersScreen({ navigation }: any) {
  const [rows, setRows] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const { ok, data } = await api<Order[]>("/api/orders");
    setRows(ok && Array.isArray(data) ? data : []);
    setLoading(false);
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  if (loading) return <Loader />;

  return (
    <FlatList
      style={{ backgroundColor: colors.bgSoft }}
      contentContainerStyle={{ padding: spacing.lg, paddingBottom: spacing.xxl, gap: spacing.md }}
      data={rows}
      keyExtractor={(o) => String(o.id)}
      refreshControl={<RefreshControl refreshing={false} onRefresh={load} tintColor={colors.brand} />}
      ListHeaderComponent={
        rows.length ? <Text style={styles.sarlavha}>Buyurtmalarim</Text> : null
      }
      ListEmptyComponent={
        <View style={styles.empty}>
          <Text style={{ fontSize: 46 }}>📦</Text>
          <Text style={styles.emptyTitle}>Buyurtmalar yo'q</Text>
          <Text style={styles.emptyHint}>Katalogdan mahsulot tanlab, birinchi buyurtmangizni bering.</Text>
        </View>
      }
      renderItem={({ item: o }) => {
        const st = HOLAT[o.holat] || { t: o.holat, c: colors.textMuted, bg: colors.secondaryBg, icon: "ellipse-outline" as const };
        const joriy = BOSQICH.indexOf(o.holat);
        const bekor = o.holat === "bekor_qilindi";
        // Balanssiz to'lov: chek yuklanmagan bo'lsa mijoz shu yerdan yuklaydi.
        const tolovKutmoqda = o.holat === "tolov_kutilmoqda";
        const chekBor = !!o.chek_rasm_url;
        return (
          <View style={styles.card}>
            {/* Yuqori qator: holat */}
            <View style={[styles.badge, { backgroundColor: st.bg }]}>
              <Ionicons name={st.icon} size={14} color={st.c} />
              <Text style={[styles.badgeText, { color: st.c }]}>{st.t}</Text>
            </View>

            {/* Buyurtma kodi — kuryerga aytiladigan asosiy narsa.
                To'lov tasdiqlanmaguncha kod berilmaydi. */}
            <Text style={styles.kodLabel}>Buyurtma kodi</Text>
            {tolovKutmoqda ? (
              <View style={styles.kodQulf}>
                <Ionicons name="lock-closed" size={17} color={colors.textFaint} />
                <Text style={styles.kodQulfText}>To'lovdan keyin ochiladi</Text>
              </View>
            ) : (
              <Text style={styles.kod}>{o.kod}</Text>
            )}

            {/* To'lov bloki — faqat to'lov kutayotgan buyurtmalarda */}
            {tolovKutmoqda && (
              <View style={styles.tolov}>
                <Text style={styles.tolovMatn}>
                  {chekBor
                    ? "Chek yuborildi. Moliya tekshirmoqda — tasdiqlangach buyurtma kodingiz shu yerda paydo bo'ladi."
                    : "Avval to'lovni amalga oshirib, chek rasmini yuklang. Chek tasdiqlangach buyurtma kodi beriladi va buyurtma do'konga yuboriladi."}
                </Text>
                <TouchableOpacity
                  style={[styles.tolovBtn, chekBor && styles.tolovBtnGhost]}
                  activeOpacity={0.85}
                  onPress={() =>
                    navigation.navigate("OrderPayment", {
                      orderId: o.id, kod: o.kod, summa: o.jami_narx,
                    })
                  }
                >
                  <Ionicons
                    name={chekBor ? "refresh-outline" : "camera-outline"}
                    size={16}
                    color={chekBor ? colors.brand : "#fff"}
                  />
                  <Text style={[styles.tolovBtnText, chekBor && { color: colors.brand }]}>
                    {chekBor ? "Chekni almashtirish" : "To'lash va chek yuklash"}
                  </Text>
                </TouchableOpacity>
              </View>
            )}

            {/* To'lov rad etilgan bo'lsa — sababi ko'rinsin */}
            {o.tolov_holati === "rad_etildi" && !!o.tolov_rad_sababi && (
              <View style={styles.radBlok}>
                <Ionicons name="alert-circle" size={16} color={colors.sale} />
                <Text style={styles.radMatn}>To'lov rad etildi: {o.tolov_rad_sababi}</Text>
              </View>
            )}

            {/* Bosqichlar yo'lagi */}
            {!bekor && !tolovKutmoqda && (
              <View style={styles.yolak}>
                {BOSQICH.map((b, i) => (
                  <View key={b} style={styles.bosqich}>
                    <View style={[styles.nuqta, i <= joriy && styles.nuqtaFaol]} />
                    {i < BOSQICH.length - 1 && (
                      <View style={[styles.chiziq, i < joriy && styles.chiziqFaol]} />
                    )}
                  </View>
                ))}
              </View>
            )}

            {/* Mahsulotlar */}
            {(o.mahsulotlar || []).slice(0, 3).map((m: any, i: number) => (
              <Text key={i} style={styles.item} numberOfLines={1}>
                • {m.nomi} × {m.soni}
              </Text>
            ))}
            {(o.mahsulotlar || []).length > 3 && (
              <Text style={styles.yana}>+ yana {(o.mahsulotlar || []).length - 3} ta</Text>
            )}

            {/* Kuryer — bosilsa qo'ng'iroq qilinadi */}
            {!!o.kuryer_tel && (
              <TouchableOpacity
                style={styles.kuryer}
                onPress={() => Linking.openURL(`tel:${o.kuryer_tel}`)}
              >
                <Ionicons name="call-outline" size={16} color={colors.store} />
                <Text style={styles.kuryerText}>Kuryer: {o.kuryer_tel}</Text>
              </TouchableOpacity>
            )}

            <View style={styles.totalRow}>
              <Text style={styles.totalLabel}>Jami</Text>
              <Text style={styles.total}>{money(o.jami_narx)} som</Text>
            </View>
          </View>
        );
      }}
    />
  );
}

const styles = StyleSheet.create({
  sarlavha: { fontSize: font.h1, fontWeight: "900", color: colors.text, letterSpacing: tracking.h1, marginBottom: spacing.xs },
  card: { backgroundColor: colors.bg, borderRadius: radius.lg, padding: spacing.lg, ...border.hair },
  badge: {
    alignSelf: "flex-start", flexDirection: "row", alignItems: "center", gap: 5,
    paddingHorizontal: 10, paddingVertical: 5, borderRadius: radius.pill,
  },
  badgeText: { fontWeight: "800", fontSize: font.tiny },
  kodLabel: { fontSize: font.tiny, color: colors.textFaint, textTransform: "uppercase", marginTop: 12, letterSpacing: 0.5 },
  kod: { fontSize: 32, fontWeight: "900", letterSpacing: 6, color: colors.brand, marginTop: 2 },
  kodQulf: { flexDirection: "row", alignItems: "center", gap: 7, marginTop: 6, marginBottom: 2 },
  kodQulfText: { color: colors.textFaint, fontWeight: "700", fontSize: font.body },

  yolak: { flexDirection: "row", alignItems: "center", marginTop: 14, marginBottom: 6 },
  bosqich: { flexDirection: "row", alignItems: "center", flex: 1 },
  nuqta: { width: 10, height: 10, borderRadius: 5, backgroundColor: colors.line },
  nuqtaFaol: { backgroundColor: colors.brand },
  chiziq: { flex: 1, height: 2, backgroundColor: colors.line },
  chiziqFaol: { backgroundColor: colors.brand },

  tolov: { marginTop: 14, gap: 10, backgroundColor: colors.bgSoft, borderRadius: radius.md, padding: 12 },
  tolovMatn: { color: colors.textMuted, fontSize: font.small, lineHeight: 19 },
  tolovBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 7,
    backgroundColor: colors.brand, borderRadius: radius.sm, paddingVertical: 13,
  },
  tolovBtnGhost: { backgroundColor: colors.bg, ...border.brand },
  tolovBtnText: { color: "#fff", fontWeight: "800", fontSize: font.small },
  radBlok: {
    flexDirection: "row", alignItems: "center", gap: 7, marginTop: 12,
    backgroundColor: colors.saleSoft, borderRadius: radius.sm, padding: 11,
  },
  radMatn: { flex: 1, color: colors.sale, fontWeight: "700", fontSize: font.small },

  item: { color: colors.text, marginTop: 6, fontSize: font.body },
  yana: { color: colors.textMuted, fontSize: font.small, marginTop: 4 },
  kuryer: {
    flexDirection: "row", alignItems: "center", gap: 6, marginTop: 10,
    backgroundColor: colors.storeSoft, borderRadius: radius.sm, padding: 10,
  },
  kuryerText: { color: colors.store, fontWeight: "700", fontSize: font.small },
  totalRow: {
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
    borderTopWidth: 1, borderTopColor: colors.lineSoft, paddingTop: 12, marginTop: 12,
  },
  totalLabel: { color: colors.textMuted },
  total: { fontWeight: "900", color: colors.gold, fontSize: font.h2 },

  empty: { alignItems: "center", marginTop: 60, gap: 8, paddingHorizontal: spacing.xl },
  emptyTitle: { fontSize: font.h2, fontWeight: "800", color: colors.text },
  emptyHint: { color: colors.textMuted, textAlign: "center", lineHeight: 20 },
});
