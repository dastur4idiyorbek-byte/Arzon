/**
 * ARZON dizayn tizimi — 2026 mobil savdo me'yorlari asosida.
 *
 * Tahlil (Uzum/Wildberries/Ozon kabi marketplace'lar + 2026 yo'nalishlari):
 *   • Yirik radius (16–28) va yumshoq, KO'P QATLAMLI soya — "qog'oz" emas,
 *     ko'tarilgan yuza hissi.
 *   • Kulrang-oq fon + oppoq kartochka: kontent ajralib turadi.
 *   • Qalin, zich sarlavhalar (letterSpacing manfiy) — zamonaviy tipografika.
 *   • Rang kam, lekin aniq: brend faqat asosiy amalda; qolgani neytral.
 *   • Barmoq uchun katta nishon (min 44px) va pastda doimiy asosiy tugma.
 *
 * Rol-rang tizimi (butun loyihada bir xil):
 *   🟠 brand — xarid/savat/asosiy amal   🟢 store — do'kon, tasdiq
 *   🟡 gold  — balans/pul                🔴 sale  — chegirma, xavfli amal
 */
export const colors = {
  brand: "#F2610C",
  brandDark: "#C84605",
  brandSoft: "#FFF0E6",
  store: "#0E7A55",
  storeSoft: "#E7F5EF",
  gold: "#B8860B",
  goldSoft: "#FBF3E0",
  sale: "#E11D48",
  saleSoft: "#FFF0F3",
  warn: "#B45309",
  info: "#1D6FB8",
  infoSoft: "#E8F1FA",

  bg: "#FFFFFF",
  /** Ekran foni — oppoq kartochkalar shu fonda "suzadi". */
  bgSoft: "#F5F5F7",
  cardTop: "#FFF8F2",
  text: "#0F1115",
  textMuted: "#6A6F7A",
  textFaint: "#9AA0AB",
  line: "#E8E9EC",
  lineSoft: "#F1F2F4",
  secondaryBg: "#F2F3F5",
  /** Skeleton (yuklanish) uchun. */
  skeleton: "#E9EAED",
  skeletonHi: "#F4F5F7",
};

export const radius = {
  xs: 10,
  sm: 14,
  md: 18,
  lg: 22,
  xl: 28,
  pill: 999,
};

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 };

export const font = {
  hero: 30,
  h1: 24,
  h2: 18,
  h3: 15,
  body: 14,
  small: 12,
  tiny: 11,
};

/** Sarlavhalar uchun zich harf oralig'i (zamonaviy ko'rinish). */
export const tracking = {
  hero: -0.8,
  h1: -0.5,
  h2: -0.3,
  normal: 0,
  wide: 0.4,
};

/**
 * Soyalar — yumshoq va keng tarqalgan (qattiq chegara o'rniga).
 * iOS shadow*, Android elevation — ikkalasi ham beriladi.
 */
export const shadow = {
  xs: {
    shadowColor: "#0F1115",
    shadowOpacity: 0.04,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 1 },
    elevation: 1,
  },
  sm: {
    shadowColor: "#0F1115",
    shadowOpacity: 0.06,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 3 },
    elevation: 2,
  },
  md: {
    shadowColor: "#0F1115",
    shadowOpacity: 0.08,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 6 },
    elevation: 5,
  },
  lg: {
    shadowColor: "#0F1115",
    shadowOpacity: 0.14,
    shadowRadius: 28,
    shadowOffset: { width: 0, height: 12 },
    elevation: 10,
  },
} as const;

/** Animatsiya davomiyligi (ms) — qisqa va bir xil bo'lsin. */
export const motion = { fast: 140, normal: 220, slow: 320 };
