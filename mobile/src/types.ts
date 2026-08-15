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
};

export type CartLine = {
  product: Product;
  soni: number;
  olcham?: string | null;
  rang?: string | null;
};

export type Order = {
  id: number;
  kod: string;
  jami_narx: number;
  holat: string;
  mahsulotlar: any[];
  yetkazish_turi?: string;
  kuryer_tel?: string | null;
};

export function effPrice(p: Product): number {
  return p.sotuv_narxi != null ? p.sotuv_narxi : p.narxi;
}
