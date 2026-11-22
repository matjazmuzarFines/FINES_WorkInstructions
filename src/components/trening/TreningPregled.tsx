"use client";

import { useMemo, useState } from "react";
import { AI_JI, kljucOcene, povprecje, type AiKoda, type TreningModel } from "@/lib/trening";
import { ujemaIskanje } from "@/lib/iskanje";
import { danesIso, prenesiXlsx } from "@/lib/excel";
import { Button } from "@/components/ui/Button";
import { FilterIskanje, FilterPolje, FilterPreklopnik, FilterVrstica } from "@/components/ui/Filtri";
import { Izvoz } from "@/components/ui/Izvoz";
import { SortTh, TabelaOkvir, useRazvrscanje } from "@/components/ui/Tabela";
import { AiLogo } from "./AiLogo";
import { SlikaModela } from "./SlikaModela";
import { casGeneracije, datumCas, podatki, trajanje } from "./oblika";

/** Povzetek enega AI-ja za en model. */
type PoAi = {
  poskusov: number;
  ocenjenih: number;
  /** Najboljše povprečje ocen med poskusi (1-5). */
  najboljsa: number | null;
  /** Vsota povprečij ocenjenih poskusov (za skupno povprečje). */
  vsotaOcen: number;
  /** Skupni čas generiranja v sekundah. */
  cas: number;
  modeliAi: string[];
  zadnji: string | null;
};

type Vrstica = { id: string; naziv: string; zahteva: number | null; slika: string | null; ai: Record<AiKoda, PoAi>; zadnji: string | null };

type Kljuc = "naziv" | `${AiKoda}_poskusi` | `${AiKoda}_ocena` | `${AiKoda}_cas` | "zadnji";
type Ocenjenost = "vsi" | "ocenjeni" | "neocenjeni";

function izracunaj(m: TreningModel, ai: AiKoda): PoAi {
  const r: PoAi = { poskusov: 0, ocenjenih: 0, najboljsa: null, vsotaOcen: 0, cas: 0, modeliAi: [], zadnji: null };
  const modeliAi = new Set<string>();
  for (const p of m.poskusi[ai]) {
    r.poskusov++;
    const meta = podatki(p.meta);
    r.cas += casGeneracije(meta?.zacetek, meta?.konec) ?? 0;
    if (meta?.ai_model) modeliAi.add(meta.ai_model);
    if (meta?.konec && (!r.zadnji || meta.konec > r.zadnji)) r.zadnji = meta.konec;
    const o = povprecje(m.ocene[kljucOcene(ai, p.poskus)]);
    if (o !== null) {
      r.ocenjenih++;
      r.vsotaOcen += o;
      r.najboljsa = r.najboljsa === null ? o : Math.max(r.najboljsa, o);
    }
  }
  r.modeliAi = [...modeliAi];
  return r;
}

const ocena = (v: number | null) => (v === null ? "" : v.toFixed(1).replace(".", ","));

/**
 * Prva stran AI treninga (zavihek Pregled): kateri treningi so narejeni, koliko poskusov z vsakim AI-jem,
 * najboljša ocena in čas generiranja. Vsebina kartice pod zavihki - filtri z izvozom, tabela, vrstica Skupaj.
 */
export function TreningPregled({
  modeli,
  url,
  onOdpri,
}: {
  modeli: TreningModel[];
  /** URL datoteke (sličica modela) - lokalni API ali podpisan URL Supabase. */
  url: (pot: string) => string;
  onOdpri: (id: string) => void;
}) {
  const [iskanje, setIskanje] = useState("");
  const [ocenjenost, setOcenjenost] = useState<Ocenjenost>("vsi");

  const vse = useMemo<Vrstica[]>(
    () =>
      modeli.map((m) => {
        const ai = Object.fromEntries(AI_JI.map((a) => [a.koda, izracunaj(m, a.koda)])) as Record<AiKoda, PoAi>;
        const info = podatki(m.info);
        return {
          id: m.id,
          naziv: info?.naziv ?? m.id,
          zahteva: info?.zahteva_id ?? null,
          slika: m.slika,
          ai,
          zadnji: AI_JI.map((a) => ai[a.koda].zadnji).filter((x): x is string => !!x).sort().pop() ?? null,
        };
      }),
    [modeli],
  );

  const sort = useRazvrscanje<Vrstica, Kljuc>({
    naziv: (r) => r.naziv,
    astra_poskusi: (r) => r.ai.astra.poskusov,
    astra_ocena: (r) => r.ai.astra.najboljsa,
    astra_cas: (r) => r.ai.astra.cas || null,
    fable_poskusi: (r) => r.ai.fable.poskusov,
    fable_ocena: (r) => r.ai.fable.najboljsa,
    fable_cas: (r) => r.ai.fable.cas || null,
    zadnji: (r) => r.zadnji,
  });

  const ocenjen = (r: Vrstica) => AI_JI.some((a) => r.ai[a.koda].ocenjenih > 0);
  const filtrirane = vse.filter(
    (r) =>
      ujemaIskanje(`${r.naziv} ${r.id} ${r.zahteva ?? ""}`, iskanje) &&
      (ocenjenost === "vsi" || (ocenjenost === "ocenjeni") === ocenjen(r)),
  );
  const vrstice = sort.razvrsti(filtrirane);
  const imaFilter = !!iskanje || ocenjenost !== "vsi";

  const skupaj = Object.fromEntries(
    AI_JI.map((a) => {
      const v = vrstice.map((r) => r.ai[a.koda]);
      const ocenjenih = v.reduce((s, x) => s + x.ocenjenih, 0);
      return [
        a.koda,
        {
          poskusov: v.reduce((s, x) => s + x.poskusov, 0),
          povprecje: ocenjenih ? v.reduce((s, x) => s + x.vsotaOcen, 0) / ocenjenih : null,
          cas: v.reduce((s, x) => s + x.cas, 0),
          modeliAi: [...new Set(v.flatMap((x) => x.modeliAi))],
        },
      ];
    }),
  ) as Record<AiKoda, { poskusov: number; povprecje: number | null; cas: number; modeliAi: string[] }>;

  function izvoziExcel() {
    const naziv = (koda: AiKoda) => AI_JI.find((a) => a.koda === koda)!.naziv;
    return prenesiXlsx(
      [
        {
          ime: "Pregled treningov",
          vrstice: vrstice.map((r) => ({
            Model: r.naziv,
            Mapa: r.id,
            Zahteva: r.zahteva,
            ...Object.fromEntries(
              AI_JI.flatMap((a) => [
                [`${naziv(a.koda)} - poskusi`, r.ai[a.koda].poskusov],
                [`${naziv(a.koda)} - najboljša ocena`, r.ai[a.koda].najboljsa === null ? null : Math.round(r.ai[a.koda].najboljsa! * 10) / 10],
                [`${naziv(a.koda)} - čas (min)`, Math.round(r.ai[a.koda].cas / 60)],
              ]),
            ),
            "Zadnji poskus": r.zadnji ? datumCas(r.zadnji) : "",
          })),
        },
      ],
      `AI_trening_pregled_${danesIso()}`,
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <FilterVrstica>
        <FilterIskanje value={iskanje} onChange={setIskanje} placeholder="Model, mapa ali zahteva" hint="Išči po nazivu modela, mapi ali zahtevi" />
        <FilterPreklopnik<Ocenjenost>
          label="Ocena"
          value={ocenjenost}
          onChange={setOcenjenost}
          options={[
            { value: "vsi", label: "Vsi", hint: "Pokaži vse modele", stevilo: vse.length },
            { value: "ocenjeni", label: "Ocenjeni", hint: "Samo modeli z vsaj eno oceno", stevilo: vse.filter(ocenjen).length },
            { value: "neocenjeni", label: "Neocenjeni", hint: "Samo modeli brez ocene", stevilo: vse.filter((r) => !ocenjen(r)).length },
          ]}
        />
        {imaFilter && (
          <FilterPolje>
            <Button
              variant="neutral"
              hint="Ponastavi iskanje in filter ocene"
              onClick={() => {
                setIskanje("");
                setOcenjenost("vsi");
              }}
            >
              Ponastavi filtre
            </Button>
          </FilterPolje>
        )}
        <Izvoz
          className="ml-auto"
          spomin="ai-trening-pregled"
          formati={[{ koda: "xlsx", label: "Excel (.xlsx)", hint: "Prenesi pregled treningov v Excel", akcija: izvoziExcel }]}
        />
      </FilterVrstica>

      <TabelaOkvir>
        <table className="w-full min-w-[56rem] text-sm">
          <thead className="fp-thead">
            <tr>
              <th className="px-2 pt-2" />
              {AI_JI.map((a) => (
                <th key={a.koda} colSpan={3} className="border-l border-ink-600 px-2 pt-2 text-center" title={`${a.naziv} (${a.orodje})`}>
                  <span className="inline-flex items-center gap-2">
                    <span className="flex h-7 w-7 items-center justify-center rounded-md bg-white p-1">
                      <AiLogo ai={a.koda} className="h-5 w-5" />
                    </span>
                    <span className="text-left leading-tight">
                      <span className="block text-fines-200">{a.naziv}</span>
                      <span className="block text-xs font-normal text-ink-300">{a.orodje}</span>
                    </span>
                  </span>
                </th>
              ))}
              <th className="border-l border-ink-600 px-2 pt-2" />
            </tr>
            <tr>
              <SortTh sort={sort} kljuc="naziv" hint="Razvrsti po nazivu modela">
                Model
              </SortTh>
              {AI_JI.map((a) => [
                <SortTh
                  key={`${a.koda}-p`}
                  sort={sort}
                  kljuc={`${a.koda}_poskusi`}
                  desno
                  className="border-l border-ink-600"
                  hint={`Razvrsti po številu poskusov ${a.naziv}`}
                >
                  Poskusi
                </SortTh>,
                <SortTh key={`${a.koda}-o`} sort={sort} kljuc={`${a.koda}_ocena`} desno hint={`Razvrsti po najboljši oceni ${a.naziv}`}>
                  Ocena
                </SortTh>,
                <SortTh key={`${a.koda}-c`} sort={sort} kljuc={`${a.koda}_cas`} desno hint={`Razvrsti po času generiranja ${a.naziv}`}>
                  Čas
                </SortTh>,
              ])}
              <SortTh sort={sort} kljuc="zadnji" className="border-l border-ink-600" hint="Razvrsti po datumu zadnjega poskusa">
                Zadnji poskus
              </SortTh>
            </tr>
          </thead>
          <tbody>
            {vrstice.map((r) => {
              const najb = AI_JI.map((a) => r.ai[a.koda].najboljsa);
              const max = najb.every((v) => v !== null) && new Set(najb).size > 1 ? Math.max(...(najb as number[])) : null;
              return (
                <tr key={r.id} className="border-b border-ink-100 hover:bg-ink-50">
                  <td className="px-2 py-1.5">
                    <button
                      type="button"
                      title={`Odpri primerjavo za ${r.naziv}`}
                      onClick={() => onOdpri(r.id)}
                      className="group flex items-center gap-3 text-left"
                    >
                      <SlikaModela src={r.slika ? url(r.slika) || null : null} naziv={r.naziv} />
                      <span className="min-w-0">
                        <span className="block font-semibold text-ink-900 group-hover:text-fines-600 group-hover:underline">{r.naziv}</span>
                        <span className="block font-mono text-xs text-ink-400">
                          {r.id}
                          {r.zahteva ? ` · zahteva #${r.zahteva}` : ""}
                        </span>
                      </span>
                    </button>
                  </td>
                  {AI_JI.map((a, i) => {
                    const x = r.ai[a.koda];
                    const boljsa = max !== null && najb[i] === max;
                    return [
                      <td key={`${a.koda}-p`} className="border-l border-ink-200 px-2 py-1.5 text-right tabular-nums" title={x.modeliAi.join(", ")}>
                        {x.poskusov}
                      </td>,
                      <td
                        key={`${a.koda}-o`}
                        className={`px-2 py-1.5 text-right tabular-nums ${boljsa ? "font-bold text-ok-600" : ""}`}
                        title={`${x.ocenjenih} od ${x.poskusov} poskusov ocenjenih${boljsa ? " - boljša ocena" : ""}`}
                      >
                        {ocena(x.najboljsa) || <span className="text-ink-400">-</span>}
                      </td>,
                      <td key={`${a.koda}-c`} className="whitespace-nowrap px-2 py-1.5 text-right tabular-nums text-ink-600">
                        {trajanje(x.cas) || <span className="text-ink-400">-</span>}
                      </td>,
                    ];
                  })}
                  <td className="whitespace-nowrap border-l border-ink-200 px-2 py-1.5 text-ink-600">{r.zadnji ? datumCas(r.zadnji) : ""}</td>
                </tr>
              );
            })}
            {vrstice.length === 0 && (
              <tr>
                <td colSpan={2 + AI_JI.length * 3} className="px-2 py-8 text-center text-sm text-ink-400">
                  {vse.length ? "Ni treningov za izbrane filtre." : "Še ni treningov."}
                </td>
              </tr>
            )}
          </tbody>
          {vrstice.length > 0 && (
            <tfoot>
              <tr className="bg-ink-800 font-bold text-white">
                <td className="px-2 py-2">Skupaj ({vrstice.length})</td>
                {AI_JI.map((a) => {
                  const s = skupaj[a.koda];
                  return [
                    <td key={`${a.koda}-p`} className="border-l border-ink-600 px-2 py-2 text-right tabular-nums" title={s.modeliAi.join(", ")}>
                      {s.poskusov}
                    </td>,
                    <td key={`${a.koda}-o`} className="px-2 py-2 text-right tabular-nums" title="Povprečje vseh ocenjenih poskusov">
                      {ocena(s.povprecje) || "-"}
                    </td>,
                    <td key={`${a.koda}-c`} className="whitespace-nowrap px-2 py-2 text-right tabular-nums">
                      {trajanje(s.cas) || "-"}
                    </td>,
                  ];
                })}
                <td className="whitespace-nowrap border-l border-ink-600 px-2 py-2 font-normal" title="Skupni čas generiranja obeh AI-jev">
                  {trajanje(AI_JI.reduce((v, a) => v + skupaj[a.koda].cas, 0))}
                </td>
              </tr>
            </tfoot>
          )}
        </table>
      </TabelaOkvir>

      <p className="text-xs text-ink-500">
        Ocena je najboljše povprečje 6 kriterijev (1-5) med poskusi, v vrstici Skupaj povprečje vseh ocenjenih poskusov; boljša ocena
        je zelena. Čas je vsota časov generiranja (meta.json). Modeli AI:{" "}
        {AI_JI.map((a) => `${a.naziv} - ${skupaj[a.koda].modeliAi.join(", ") || "-"}`).join("; ")}.
      </p>
    </div>
  );
}
