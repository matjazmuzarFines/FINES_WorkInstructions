import type { AiKoda, Json } from "@/lib/trening";

/** Barva AI-ja na strani (trak, značka) - Fines barve: Astra temno siva, Fable oranžna. */
export const BARVA_AI: Record<AiKoda, { trak: string; znacka: string; crka: string }> = {
  astra: { trak: "border-t-ink-700", znacka: "bg-ink-700 text-white", crka: "A" },
  fable: { trak: "border-t-fines-500", znacka: "bg-fines-500 text-white", crka: "F" },
};

export function velikost(b: number) {
  if (b < 1024) return `${b} B`;
  if (b < 1024 ** 2) return `${(b / 1024).toFixed(0)} KB`;
  if (b < 1024 ** 3) return `${(b / 1024 ** 2).toFixed(1).replace(".", ",")} MB`;
  return `${(b / 1024 ** 3).toFixed(2).replace(".", ",")} GB`;
}

export function datumCas(iso?: string) {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleString("sl-SI", { day: "numeric", month: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

/** 75 -> "1 min 15 s" */
export function trajanje(s: number | null | undefined) {
  if (s === null || s === undefined || !Number.isFinite(s) || s < 0) return "";
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sek = Math.round(s % 60);
  if (h) return `${h} h ${m} min`;
  if (m) return `${m} min ${sek} s`;
  return `${sek} s`;
}

/** Čas generacije iz meta.json (konec - začetek) v sekundah. */
export function casGeneracije(zacetek?: string, konec?: string): number | null {
  if (!zacetek || !konec) return null;
  const s = (new Date(konec).getTime() - new Date(zacetek).getTime()) / 1000;
  return Number.isFinite(s) && s >= 0 ? s : null;
}

export const podatki = <T,>(j: Json<T>): T | null => (j && "podatki" in j ? j.podatki : null);
export const napakaJson = <T,>(j: Json<T>): string | null => (j && "napaka" in j ? j.napaka : null);

export const STATUS: Record<string, { label: string; cls: string }> = {
  uspeh: { label: "Uspeh", cls: "bg-ok-50 text-ok-600" },
  delno: { label: "Delno", cls: "bg-warn-50 text-warn-700" },
  neuspeh: { label: "Neuspeh", cls: "bg-nok-50 text-nok-600" },
};
