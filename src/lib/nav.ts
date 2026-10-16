import type { LucideIcon } from "lucide-react";
import { BookOpenText, Factory, Link2, ListChecks, Settings, ShieldCheck } from "lucide-react";

export type NavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
  hint: string;
  kmalu?: boolean;
  /** Podmeni: klik na postavko ga razpre (postavka sama ni stran). */
  children?: NavItem[];
};

/** Razdelek modula - v meniju oranžen naslov in tanka oranžna črta. */
export type NavSekcija = {
  label: string;
  items: NavItem[];
};

/** Modul aplikacije (npr. Proizvodnja, Admin). */
export type NavGroup = {
  label: string;
  icon: LucideIcon;
  sekcije: NavSekcija[];
};

/** Meni je viden samo med admin dostopom. */
export const NAV: NavGroup[] = [
  {
    label: "Proizvodnja",
    icon: Factory,
    sekcije: [
      {
        label: "Rutinsko delo",
        items: [
          {
            label: "Navodila",
            href: "/proizvodnja/navodila",
            icon: BookOpenText,
            hint: "Preglej vsa navodila za delo",
          },
        ],
      },
    ],
  },
  {
    label: "Admin",
    icon: ShieldCheck,
    sekcije: [
      {
        label: "Podatki navodil",
        items: [
          {
            label: "Programi",
            href: "/admin/programi",
            icon: ListChecks,
            hint: "Izdelava in urejanje programov navodil",
          },
          {
            label: "Povezave",
            href: "/admin/povezave",
            icon: Link2,
            hint: "Poveži programe navodil z identi",
          },
          {
            label: "Nastavitve",
            href: "/admin/nastavitve",
            icon: Settings,
            hint: "Sekcije, podsekcije in uvoz šifer",
          },
        ],
      },
    ],
  },
];

/** Ali je stran (ali njena podstran) na poti `href`. */
const naPoti = (pathname: string, href: string) => pathname === href || pathname.startsWith(`${href}/`);

/** Postavka z najdaljšim ujemanjem poti. */
export function aktivnaPostavka(items: NavItem[], pathname: string): NavItem | null {
  return (
    items
      .filter((i) => naPoti(pathname, i.href))
      .sort((a, b) => b.href.length - a.href.length)[0] ?? null
  );
}

export function findNav(pathname: string) {
  for (const group of NAV) {
    for (const sekcija of group.sekcije) {
      const item = aktivnaPostavka(sekcija.items, pathname);
      if (item) return { group, sekcija, item, sub: item.children ? aktivnaPostavka(item.children, pathname) : null };
    }
  }
  return null;
}

/** Vse strani (postavke brez podmenija + postavke podmenijev). */
export function listiNav(items: NavItem[]): NavItem[] {
  return items.flatMap((i) => i.children ?? [i]);
}

/** Kam pelje gumb "Nazaj": na nadrejeno stran (strani iz menija in navodila vodijo domov). */
export function parentHref(pathname: string): string {
  const deli = pathname.split("/").filter(Boolean);
  deli.pop();
  const nadrejena = `/${deli.join("/")}`;
  const strani = NAV.flatMap((g) => g.sekcije.flatMap((s) => listiNav(s.items)));
  if (strani.some((i) => i.href === pathname)) return "/";
  return strani.some((i) => i.href === nadrejena) ? nadrejena : "/";
}
