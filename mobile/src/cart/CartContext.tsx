import React, { createContext, useContext, useMemo, useState } from "react";
import { CartLine, Product, effPrice } from "../types";

type CartState = {
  lines: CartLine[];
  count: number;
  subtotal: number;
  add: (p: Product, olcham?: string | null, rang?: string | null) => void;
  changeQty: (key: string, d: number) => void;
  clear: () => void;
  keyOf: (l: CartLine) => string;
};

const Ctx = createContext<CartState>({} as CartState);
export const useCart = () => useContext(Ctx);

const key = (p: Product, olcham?: string | null, rang?: string | null) =>
  `${p.id}|${olcham || ""}|${rang || ""}`;

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [lines, setLines] = useState<CartLine[]>([]);

  function add(p: Product, olcham?: string | null, rang?: string | null) {
    setLines((prev) => {
      const k = key(p, olcham, rang);
      const i = prev.findIndex((l) => key(l.product, l.olcham, l.rang) === k);
      if (i >= 0) {
        const next = [...prev];
        next[i] = { ...next[i], soni: next[i].soni + 1 };
        return next;
      }
      return [...prev, { product: p, soni: 1, olcham, rang }];
    });
  }

  function changeQty(k: string, d: number) {
    setLines((prev) =>
      prev
        .map((l) => (key(l.product, l.olcham, l.rang) === k ? { ...l, soni: l.soni + d } : l))
        .filter((l) => l.soni > 0)
    );
  }

  const { count, subtotal } = useMemo(() => {
    let c = 0, s = 0;
    for (const l of lines) {
      c += l.soni;
      s += effPrice(l.product) * l.soni;
    }
    return { count: c, subtotal: s };
  }, [lines]);

  return (
    <Ctx.Provider
      value={{ lines, count, subtotal, add, changeQty, clear: () => setLines([]),
               keyOf: (l) => key(l.product, l.olcham, l.rang) }}
    >
      {children}
    </Ctx.Provider>
  );
}
