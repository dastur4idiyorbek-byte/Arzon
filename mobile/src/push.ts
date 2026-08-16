/**
 * Push-bildirishnoma (Phase 5) — Expo push token olish va backendга yuborish.
 *
 * Oqim:
 *   1. Foydalanuvchi kirгач `registerPush()` chaqiriladi.
 *   2. Ruxsat so'raladi, Expo push token olinadi.
 *   3. Token backendга (`POST /api/push/register`) yuboriladi.
 *   4. Backend buyurtma/balans/arenda hodisalarida shu token orqali push yuboradi.
 *
 * Eslatma: push haqiqiy qurilmада ishlaydi (simulyatorда emas) va Expo hisobи
 * (projectId) build qilingач to'liq ishlaydi.
 */
import { Platform } from "react-native";
import Constants from "expo-constants";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import { api } from "./api";

// Ilova ochiqда ham bildirishnoma ko'rinsin.
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

let registered = false;

export async function registerPush(): Promise<void> {
  if (registered) return;
  try {
    if (!Device.isDevice) return; // simulyatorда push yo'q

    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("default", {
        name: "ARZON",
        importance: Notifications.AndroidImportance.HIGH,
        lightColor: "#E8590C",
      });
    }

    const existing = await Notifications.getPermissionsAsync();
    let status = existing.status;
    if (status !== "granted") {
      const req = await Notifications.requestPermissionsAsync();
      status = req.status;
    }
    if (status !== "granted") return;

    const projectId =
      (Constants.expoConfig?.extra as any)?.eas?.projectId ||
      (Constants as any)?.easConfig?.projectId;
    const tokenData = await Notifications.getExpoPushTokenAsync(
      projectId ? { projectId } : undefined
    );
    const token = tokenData.data;
    if (token) {
      await api("/api/push/register", { method: "POST", body: { token } });
      registered = true;
    }
  } catch (e) {
    // Push muvaffaqiyatsiz bo'lsa ilova baribir ishlayveradi.
    console.warn("Push register xatolik:", e);
  }
}

export async function unregisterPush(): Promise<void> {
  registered = false;
  try {
    await api("/api/push/register", { method: "DELETE" });
  } catch {
    // e'tiborsiz
  }
}
