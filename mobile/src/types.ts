import { API_URL } from "./api";
export type Product = {
  id: number;
  nomi: string;
  tavsif?: string | null;
  narxi: number;
  sotuv_narxi?: number | null;
  skidka_foizi?: number;
  rasm_url?: string | null;
  rasm_urls?: string[];
  korinish?: string;
  tugadi?: boolean;
  store_nomi?: string | null;
  store_id: number;
  olcham?: string | null;
  rang?: string | null;
  /** Chegirma qachon tugashi (ISO) — taymer shu bo'yicha ishlaydi. */
  skidka_muddati?: string | null;
  /** Rasm nisbati: '1:1' | '4:3' | '3:4' | '9:16' | '16:9'. */
  rasm_nisbati?: string | null;
  /** Omborda qolgan dona (null = cheksiz). */
  miqdor?: number | null;
};

export type CartLine = {
  product: Product;
  soni: number;
  olcham?: string | null;
  rang?: string | null;
  /** Chegirma qachon tugashi (ISO) — taymer shu bo'yicha ishlaydi. */
  skidka_muddati?: string | null;
  /** Rasm nisbati: '1:1' | '4:3' | '3:4' | '9:16' | '16:9'. */
  rasm_nisbati?: string | null;
  /** Omborda qolgan dona (null = cheksiz). */
  miqdor?: number | null;
};

export type Order = {
  id: number;
  kod: string;
  jami_narx: number;
  holat: string;
  mahsulotlar: any[];
  yetkazish_turi?: string;
  kuryer_tel?: string | null;
  store_id?: number;
  /** "kutilmoqda" | "tasdiqlandi" | "rad_etildi" — chek holati. */
  tolov_holati?: string | null;
  /** Yuklangan chek rasmi (nisbiy manzil). */
  chek_rasm_url?: string | null;
  tolov_rad_sababi?: string | null;
};

export function effPrice(p: Product): number {
  return p.sotuv_narxi != null ? p.sotuv_narxi : p.narxi;
}

/** Nisbiy manzilni (/media/...) to'liq URL'ga aylantiradi. */
export function toliqUrl(u?: string | null): string | null {
  if (!u) return null;
  return u.startsWith("http") ? u : API_URL + u;
}

/** Mahsulotning BIRINCHI rasmi (kartochka uchun). */
export function rasmUrl(p: Product): string | null {
  return toliqUrl(p.rasm_url || (p.rasm_urls && p.rasm_urls[0]) || null);
}

/** Mahsulotning BARCHA rasmlari (karusel uchun, takrorsiz). */
export function rasmlar(p: Product): string[] {
  const hammasi = [p.rasm_url, ...(p.rasm_urls || [])];
  const koringan = new Set<string>();
  const natija: string[] = [];
  for (const u of hammasi) {
    const t = toliqUrl(u);
    if (t && !koringan.has(t)) {
      koringan.add(t);
      natija.push(t);
    }
  }
  return natija;
}

/** Rasm nisbati matnini (masalan "4:3") son nisbatiga aylantiradi. */
export function nisbat(p: Product): number {
  const [w, h] = (p.rasm_nisbati || "1:1").split(":").map(Number);
  return w > 0 && h > 0 ? w / h : 1;
}
