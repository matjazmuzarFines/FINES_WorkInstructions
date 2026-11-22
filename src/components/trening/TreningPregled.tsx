"use client";

import type { CSSProperties } from "react";
import { ArrowRight } from "lucide-react";
import { AI_JI, kljucOcene, povprecje, type AiKoda, type TreningModel } from "@/lib/trening";
import { TabelaOkvir } from "@/components/ui/Tabela";
import { BARVA_AI, casGeneracije, datumCas, podatki, trajanje } from "./oblika";

type PoAi = {
  poskusov: number;
  ocenjenih: number;
  /** Najboljše povprečje ocen med poskusi. */
  najboljsa: number | null;
  /** Vsota povprečij ocenjenih poskusov (za skupno povprečje). */
  vsotaOcen: number;
  cas: number;
  modeliAi: Set<string>;
  zadnji: string | null;
};

function izracunaj(m: TreningModel, ai: AiKoda): PoAi {
  const r: PoAi = { poskusov: 0, ocenjenih: 0, najboljsa: null, vsotaOcen: 0, cas: 0, modeliAi: new Set(), zadnji: null };
  for (const p of m.poskusi[ai]) {
    r.poskusov++;
    const meta = podatki(p.meta);
    r.cas += casGeneracije(meta?.zacetek, meta?.konec) ?? 0;
    if (meta?.ai_model) r.modeliAi.add(meta.ai_model);
    if (meta?.konec && (!r.zadnji || meta.konec > r.zadnji)) r.zadnji = meta.konec;
    const o = povprecje(m.ocene[kljucOcene(ai, p.poskus)]);
    if (o !== null) {
      r.ocenjenih++;
      r.vsotaOcen += o;
      r.najboljsa = r.najboljsa === null ? o : Math.max(r.najboljsa, o);
    }
  }
  return r;
}

const ocena = (v: number | null) => (v === null ? "-" : v.toFixed(1).replace(".", ","));

/** Prva stran AI treninga: katere treninge smo naredili, koliko poskusov z vsakim AI-jem in koliko časa. */
export function TreningPregled({ modeli, onOdpri }: { modeli: TreningModel[]; onOdpri: (id: string) => void }) {
  const vrstice = modeli.map((m) => ({
    m,
    naziv: podatki(m.info)?.naziv ?? m.id,
    zahteva: podatki(m.info)?.zahteva_id,
    ai: Object.fromEntries(AI_JI.map((a) => [a.koda, izracunaj(m, a.koda)])) as Record<AiKoda, PoAi>,
  }));
  const skupaj = Object.fromEntries(
    AI_JI.map((a) => {
      const v = vrstice.map((x) => x.ai[a.koda]);
      const ocenjenih = v.reduce((s, x) => s + x.ocenjenih, 0);
      return [
        a.koda,
        {
          poskusov: v.reduce((s, x) => s + x.poskusov, 0),
          ocenjenih,
          povprecje: ocenjenih ? v.reduce((s, x) => s + x.vsotaOcen, 0) / ocenjenih : null,
          cas: v.reduce((s, x) => s + x.cas, 0),
          modeliAi: [...new Set(v.flatMap((x) => [...x.modeliAi]))],
        },
      ];
    }),
  ) as Record<AiKoda, { poskusov: number; ocenjenih: number; povprecje: number | null; cas: number; modeliAi: string[] }>;
  const casSkupaj = AI_JI.reduce((s, a) => s + skupaj[a.koda].cas, 0);
  const poskusovSkupaj = AI_JI.reduce((s, a) => s + skupaj[a.koda].poskusov, 0);

  return (
    <section className="fp-card flex flex-col gap-3 p-3 sm:p-4" aria-label="Pregled treningov">
      <div>
        <h2 className="text-lg font-bold text-ink-900">Pregled treningov</h2>
        <p className="text-sm text-ink-500">
          {vrstice.length} {vrstice.length === 1 ? "model" : "modelov"} · {poskusovSkupaj} poskusov · skupni čas generiranja {trajanje(casSkupaj) || "0 s"}.
          Ocena je povprečje 6 kriterijev (1-5); v tabeli je najboljši poskus. Klik na model odpre primerjavo.
        </p>
      </div>

      {vrstice.length === 0 ? (
        <p className="rounded-lg border border-dashed border-ink-300 bg-ink-50 p-6 text-center text-sm text-ink-600">Še ni treningov.</p>
      ) : (
        <TabelaOkvir className="rounded-lg">
          <table className="w-full min-w-[52rem] text-sm" style={{ "--fp-thead-top": "0px" } as CSSProperties}>
            <thead className="fp-thead">
              <tr>
                <th className="px-2 py-2 text-left">Model</th>
                {AI_JI.map((a) => (
                  <th key={a.koda} colSpan={3} className="border-l border-ink-600 px-2 py-2 text-center" title={`${a.naziv} (${a.orodje})`}>
                    <span className={`mr-1 inline-flex h-4 w-4 items-center justify-center rounded-full text-[9px] ${BARVA_AI[a.koda].znacka}`}>
                      {BARVA_AI[a.koda].crka}
                    </span>
                    {a.naziv}
                  </th>
                ))}
                <th className="border-l border-ink-600 px-2 py-2 text-left">Zadnji poskus</th>
              </tr>
              <tr>
                <th className="px-2 pb-2" />
                {AI_JI.map((a) => [
                  <th key={`${a.koda}-p`} className="border-l border-ink-600 px-2 pb-2 text-center font-normal" title="Število poskusov">
                    Poskusi
                  </th>,
                  <th key={`${a.koda}-o`} className="px-2 pb-2 text-center font-normal" title="Najboljša povprečna ocena (1-5)">
                    Ocena
                  </th>,
                  <th key={`${a.koda}-c`} className="px-2 pb-2 text-center font-normal" title="Skupni čas generiranja vseh poskusov">
                    Čas
                  </th>,
                ])}
                <th className="border-l border-ink-600 px-2 pb-2" />
              </tr>
            </thead>
            <tbody>
              {vrstice.map(({ m, naziv, zahteva, ai }) => {
                const najb = AI_JI.map((a) => ai[a.koda].najboljsa);
                const max = najb.every((v) => v !== null) && new Set(najb).size > 1 ? Math.max(...(najb as number[])) : null;
                const zadnji = AI_JI.map((a) => ai[a.koda].zadnji).filter((x): x is string => !!x).sort().pop();
                return (
                  <tr key={m.id} className="border-b border-ink-100 hover:bg-ink-50">
                    <td className="px-2 py-2">
                      <button
                        type="button"
                        title={`Odpri primerjavo za ${naziv}`}
                        onClick={() => onOdpri(m.id)}
                        className="group flex items-center gap-2 text-left font-semibold text-ink-900 hover:text-fines-600"
                      >
                        <span>
                          {naziv}
                          <span className="block font-mono text-[11px] font-normal text-ink-400">
                            {m.id}
                            {zahteva ? ` · zahteva #${zahteva}` : ""}
                          </span>
                        </span>
                        <ArrowRight className="h-4 w-4 shrink-0 opacity-0 group-hover:opacity-100" aria-hidden />
                      </button>
                    </td>
                    {AI_JI.map((a, i) => {
                      const x = ai[a.koda];
                      return [
                        <td key={`${a.koda}-p`} className="border-l border-ink-100 px-2 py-2 text-center font-semibold" title={[...x.modeliAi].join(", ")}>
                          {x.poskusov}
                        </td>,
                        <td
                          key={`${a.koda}-o`}
                          className={`px-2 py-2 text-center ${max !== null && najb[i] === max ? "bg-ok-50 font-bold text-ok-600" : "text-ink-800"}`}
                          title={`${x.ocenjenih} od ${x.poskusov} poskusov ocenjenih`}
                        >
                          {ocena(x.najboljsa)}
                        </td>,
                        <td key={`${a.koda}-c`} className="px-2 py-2 text-center text-ink-600">
                          {trajanje(x.cas) || "-"}
                        </td>,
                      ];
                    })}
                    <td className="border-l border-ink-100 px-2 py-2 text-ink-600">{zadnji ? datumCas(zadnji) : "-"}</td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="bg-ink-100 font-bold text-ink-900">
                <td className="px-2 py-2">Skupaj</td>
                {AI_JI.map((a) => {
                  const s = skupaj[a.koda];
                  return [
                    <td key={`${a.koda}-p`} className="border-l border-ink-200 px-2 py-2 text-center" title={s.modeliAi.join(", ")}>
                      {s.poskusov}
                    </td>,
                    <td key={`${a.koda}-o`} className="px-2 py-2 text-center" title="Povprečje vseh ocenjenih poskusov">
                      {ocena(s.povprecje)}
                    </td>,
                    <td key={`${a.koda}-c`} className="px-2 py-2 text-center">
                      {trajanje(s.cas) || "-"}
                    </td>,
                  ];
                })}
                <td className="border-l border-ink-200 px-2 py-2 font-normal text-ink-600">{trajanje(casSkupaj)}</td>
              </tr>
            </tfoot>
          </table>
        </TabelaOkvir>
      )}

      <div className="grid gap-2 text-xs text-ink-500 sm:grid-cols-2">
        {AI_JI.map((a) => (
          <p key={a.koda}>
            <strong className="text-ink-700">{a.naziv}</strong> ({a.orodje}): modeli v poskusih{" "}
            {skupaj[a.koda].modeliAi.length ? skupaj[a.koda].modeliAi.join(", ") : "-"}
          </p>
        ))}
      </div>
    </section>
  );
}
