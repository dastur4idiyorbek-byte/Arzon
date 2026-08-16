/**
 * ARZON dizayn tizimi.
 *
 * Rol-rang tizimi (butun loyihada bir xil — Mini App bilan ham):
 *   🟠 brand  — xarid/savat/asosiy amal
 *   🟢 store  — do'kon, tasdiq, "sotib olish"
 *   🟡 gold   — balans/pul
 *   🔴 sale   — chegirma foizi, xavfli amal
 */
export const colors = {
  brand: "#E8590C",
  brandDark: "#C84605",
  brandSoft: "#FFF1E8", // brend fonli yumshoq maydon
  store: "#0F6B4C",
  storeSoft: "#E8F3EF",
  gold: "#C9971A",
  goldSoft: "#FDF6E3",
  sale: "#E01E1E",
  saleSoft: "#FDECEC",
  warn: "#B33A00",
  info: "#1D6FB8",

  bg: "#FFFFFF",
  bgSoft: "#F7F7F8", // ekran foni (kartochkalar ajralib tursin)
  cardTop: "#FFF8F2",
  text: "#141414",
  textMuted: "#6B6B6B",
  textFaint: "#9A9A9A",
  line: "#EAEAEA",
  lineSoft: "#F1F1F2",
  secondaryBg: "#F4F4F5",
};

export const radius = { xs: 8, sm: 12, md: 14, lg: 18, xl: 24, pill: 999 };

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 };

export const font = {
  h1: 24,
  h2: 18,
  h3: 15,
  body: 14,
  small: 12,
  tiny: 11,
};

/**
 * Soyalar — kartochkalarga "qog'ozga chizilgan" emas, ko'tarilgan ko'rinish
 * beradi. iOS soyani shadow* bilan, Android esa elevation bilan chizadi,
 * shuning uchun ikkalasi ham beriladi.
 */
export const shadow = {
  sm: {
    shadowColor: "#000",
    shadowOpacity: 0.06,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  md: {
    shadowColor: "#000",
    shadowOpacity: 0.09,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  lg: {
    shadowColor: "#000",
    shadowOpacity: 0.12,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 8 },
    elevation: 8,
  },
} as const;
