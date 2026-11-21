"use client";

import { Fragment, type CSSProperties, type ReactNode } from "react";
import { AI_JI, KRITERIJI, kljucOcene, povprecje, type AiKoda, type Ocena, type Poskus } from "@/lib/trening";
import { BARVA_AI, STATUS, casGeneracije, podatki, trajanje } from "./oblika";

type Stran = { poskus: Poskus | null; ocena: Ocena | undefined; dolzina: number | null };

/** Primerjava izbranih poskusov obeh AI-jev v eni tabeli; boljša ocena je zelena. */
export function PrimerjavaTabela({ strani }: { strani: Record<AiKoda, Stran> }) {
  const vrstica = (naslov: string, hint: string, celica: (s: Stran) => ReactNode, stevilo?: (s: Stran) => number | null) => {
    const vrednosti = AI_JI.map((a) => stevilo?.(strani[a.koda]) ?? null);
    const max = vrednosti.every((v) => v !== null) && new Set(vrednosti).size > 1 ? Math.max(...(vrednosti as number[])) : null;
    return (
      <tr className="border-b border-ink-100">
        <th scope="row" className="px-3 py-2 text-left font-semibold text-ink-700" title={hint}>
          {naslov}
        </th>
        {AI_JI.map((a, i) => (
          <td
            key={a.koda}
            className={`px-3 py-2 text-center ${max !== null && vrednosti[i] === max ? "bg-ok-50 font-bold text-ok-600" : "text-ink-800"}`}
          >
            {celica(strani[a.koda])}
          </td>
        ))}
      </tr>
    );
  };

  const ocena = (s: Stran, k: (typeof KRITERIJI)[number]["koda"]) => s.ocena?.kriteriji?.[k] ?? null;

  return (
    <section className="fp-card p-3 sm:p-4" aria-label="Primerjava">
      <h2 className="text-lg font-bold text-ink-900">Primerjava</h2>
      <p className="mb-3 text-sm text-ink-500">Izbrana poskusa drug ob drugem. Zeleno je boljša ocena.</p>
      <div className="overflow-x-auto rounded-lg" style={{ "--fp-thead-top": "0px" } as CSSProperties}>
        <table className="w-full min-w-[26rem] text-sm">
          <thead className="fp-thead">
            <tr>
              <th className="px-3 py-2">Kriterij</th>
              {AI_JI.map((a) => (
                <th key={a.koda} className="px-3 py-2 text-center">
                  <span className={`mr-2 inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] ${BARVA_AI[a.koda].znacka}`}>
                    {BARVA_AI[a.koda].crka}
                  </span>
                  {a.naziv}
                  {strani[a.koda].poskus && <span className="ml-1 font-normal normal-case text-ink-300">· {strani[a.koda].poskus!.poskus}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {vrstica("Status", "Status iz meta.json", (s) => {
              const st = podatki(s.poskus?.meta ?? null)?.status;
              if (!st) return "-";
              const o = STATUS[st] ?? { label: st, cls: "bg-ink-100 text-ink-700" };
              return <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${o.cls}`}>{o.label}</span>;
            })}
            {vrstica("Deli", "Število delov v deli.json", (s) => podatki(s.poskus?.deli ?? null)?.length ?? "-")}
            {vrstica("Koraki", "Število korakov v koraki.json", (s) => podatki(s.poskus?.koraki ?? null)?.length ?? "-")}
            {vrstica("Dolžina videa", "Dolžina video.mp4", (s) => trajanje(s.dolzina) || (s.poskus?.video ? "..." : "ni videa"))}
            {vrstica("Čas izdelave", "Od začetka do konca poskusa (meta.json)", (s) => {
              const m = podatki(s.poskus?.meta ?? null);
              return trajanje(casGeneracije(m?.zacetek, m?.konec)) || "-";
            })}
            {KRITERIJI.map((k) => (
              <Fragment key={k.koda}>
                {vrstica(k.naziv, k.opis, (s) => ocena(s, k.koda) ?? "-", (s) => ocena(s, k.koda))}
              </Fragment>
            ))}
            {vrstica(
              "Povprečje",
              "Povprečje vpisanih ocen",
              (s) => povprecje(s.ocena)?.toFixed(1).replace(".", ",") ?? "-",
              (s) => povprecje(s.ocena),
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export const ocenaZa = (ocene: Record<string, Ocena>, ai: AiKoda, p: Poskus | null) => (p ? ocene[kljucOcene(ai, p.poskus)] : undefined);
