/**
 * Havo orqali yangilanish (OTA) — ilova o'zini yangilaydi.
 *
 * NEGA: har o'zgarishda yangi APK tarqatish juda noqulay. `expo-updates`
 * bilan ekranlar/tugmalar/dizayn o'zgarishi ilovaga o'zi tushadi —
 * foydalanuvchi hech narsa yuklamaydi.
 *
 * QANDAY: ilova ochilganда yangilanish bor-yo'qligi tekshiriladi. Bo'lsa —
 * fonда yuklab olinadi va DARHOL qo'llanadi (ilova o'zi qayta yuklanadi).
 *
 * ESLATMA: bu FAQAT tayyor build (APK)да ishlaydi. Expo Go / dev rejимда
 * o'tkazib yuboriladi. Yangi NATIVE kutubxona qo'shilса — yangi APK kerak.
 */
import { useEffect, useState } from "react";
import * as Updates from "expo-updates";

export type OtaHolat = "tekshirilmoqda" | "yuklanmoqda" | "yoq" | "xato";

export function useOtaUpdate() {
  const [holat, setHolat] = useState<OtaHolat>("tekshirilmoqda");

  useEffect(() => {
    let bekor = false;

    (async () => {
      // Dev rejимда (Expo Go / metro) yangilanish yo'q — o'tkazamiz.
      if (__DEV__ || !Updates.isEnabled) {
        if (!bekor) setHolat("yoq");
        return;
      }
      try {
        const natija = await Updates.checkForUpdateAsync();
        if (bekor) return;
        if (!natija.isAvailable) {
          setHolat("yoq");
          return;
        }
        setHolat("yuklanmoqda");
        await Updates.fetchUpdateAsync();
        if (bekor) return;
        // Yangi versiyani darhol qo'llaymiz (ilova qayta yuklanadi).
        await Updates.reloadAsync();
      } catch {
        // Internet yo'q yoki server javob bermadi — ilova eski versiyada
        // muammosiz ishlayveradi.
        if (!bekor) setHolat("xato");
      }
    })();

    return () => {
      bekor = true;
    };
  }, []);

  return holat;
}
