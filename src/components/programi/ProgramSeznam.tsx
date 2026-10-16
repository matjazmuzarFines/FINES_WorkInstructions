"use client";

import { useMemo, useState, type CSSProperties, type ReactNode } from "react";
import { RotateCcw } from "lucide-react";
import { podsekcijaLabel, type Program, type Sifranti } from "@/lib/navodila";
import { Button } from "@/components/ui/Button";
import { FilterIskanje, FilterPolje, FilterVrstica } from "@/components/ui/Filtri";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { SortTh, useRazvrscanje } from "@/components/ui/Tabela";
import { ujemaIskanje } from "@/lib/iskanje";

type Kljuc = "id" | "interni" | "naziv" | "druzine" | "koraki";

/** Kode družin programa, npr. "OCB, OCB-e". */
export function druzineProgramaText(p: Program, s: Sifranti) {
  return p.druzine
    .map((id) => s.druzine.find((d) => d.id === id)?.koda)
    .filter(Boolean)
    .sort()
    .join(", ");
}

/**
 * Seznam programov s filtri (iskanje, podsekcije, družine) in razvrščanjem.
 * Klik na vrstico izbere program. Uporabljen na straneh Programi in Povezave.
 */
export function ProgramSeznam({
  programi,
  sifranti,
  izbran,
  onIzberi,
  naslov,
  gumbi,
}: {
  programi: Program[];
  sifranti: Sifranti;
  izbran: number | null;
  onIzberi: (id: number) => void;
  naslov: string;
  gumbi?: ReactNode;
}) {
  const [iskanje, setIskanje] = useState("");
  const [podsekcije, setPodsekcije] = useState<string[]>([]);
  const [druzine, setDruzine] = useState<string[]>([]);

  const podLabel = useMemo(() => {
    const m = new Map<number, string>();
    for (const p of sifranti.podsekcije) m.set(p.id, podsekcijaLabel(p, sifranti.sekcije));
    return m;
  }, [sifranti]);
  const druzinaKoda = useMemo(() => new Map(sifranti.druzine.map((d) => [d.id, d.koda])), [sifranti]);

  const sort = useRazvrscanje<Program, Kljuc>({
    id: (p) => p.id,
    interni: (p) => p.interni_id,
    naziv: (p) => p.naziv,
    druzine: (p) => druzineProgramaText(p, sifranti),
    koraki: (p) => p.stKorakov,
  });

  const filtrirani = sort.razvrsti(
    programi.filter((p) => {
      if (!ujemaIskanje([p.interni_id, p.naziv, p.opis ?? "", String(p.id)].join(" "), iskanje)) return false;
      if (podsekcije.length && !p.podsekcije.some((id) => podsekcije.includes(podLabel.get(id) ?? ""))) return false;
      if (druzine.length && !p.druzine.some((id) => druzine.includes(druzinaKoda.get(id) ?? ""))) return false;
      return true;
    }),
  );
  const imaFilter = iskanje || podsekcije.length || druzine.length;

  return (
    <section className="fp-card flex min-w-0 flex-col gap-3 p-3 sm:p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-[min(100%,10rem)] flex-1">
          <h2 className="text-lg font-bold text-ink-900">{naslov}</h2>
          <p className="text-xs text-ink-500">
            {filtrirani.length} / {programi.length} programov
          </p>
        </div>
        {gumbi && <div className="flex flex-wrap gap-2">{gumbi}</div>}
      </div>

      <FilterVrstica>
        <FilterIskanje
          value={iskanje}
          onChange={setIskanje}
          placeholder="ID, ime ali opis ..."
          hint="Išči program po ID, imenu ali opisu"
          className="w-full"
        />
        <div className="min-w-40 flex-1">
          <MultiSelect
            label="Podsekcije"
            options={sifranti.podsekcije.map((p) => podLabel.get(p.id)!)}
            value={podsekcije}
            onChange={setPodsekcije}
            hint="Prikaži programe izbranih podsekcij"
          />
        </div>
        <div className="min-w-32 flex-1">
          <MultiSelect
            label="Družine"
            options={sifranti.druzine.map((d) => d.koda)}
            value={druzine}
            onChange={setDruzine}
            hint="Prikaži programe izbranih družin artiklov"
          />
        </div>
        {imaFilter ? (
          <FilterPolje>
            <Button
              hint="Ponastavi vse filtre seznama"
              variant="neutral"
              icon={RotateCcw}
              onClick={() => {
                setIskanje("");
                setPodsekcije([]);
                setDruzine([]);
              }}
            >
              <span className="hidden sm:inline">Ponastavi</span>
            </Button>
          </FilterPolje>
        ) : null}
      </FilterVrstica>

      <div
        className="max-h-[calc(100dvh-20rem)] min-h-48 overflow-auto rounded-lg"
        style={{ "--fp-thead-top": "0px" } as CSSProperties}
      >
        <table className="w-full text-sm">
          <thead className="fp-thead">
            <tr>
              <SortTh sort={sort} kljuc="id" className="w-12">
                ID
              </SortTh>
              <SortTh sort={sort} kljuc="interni">
                Interni ID
              </SortTh>
              <SortTh sort={sort} kljuc="naziv">
                Ime in opis
              </SortTh>
              <SortTh sort={sort} kljuc="druzine" className="hidden sm:table-cell">
                Družine
              </SortTh>
              <SortTh sort={sort} kljuc="koraki" desno hint="Razvrsti po številu korakov">
                Kor.
              </SortTh>
            </tr>
          </thead>
          <tbody>
            {filtrirani.map((p) => {
              const aktiven = p.id === izbran;
              return (
                <tr
                  key={p.id}
                  onClick={() => onIzberi(p.id)}
                  title={`Odpri program ${p.interni_id}`}
                  className={`cursor-pointer border-b border-ink-100 transition-colors ${
                    aktiven ? "bg-fines-50 shadow-[inset_4px_0_0_var(--color-fines-500)]" : "hover:bg-ink-50"
                  }`}
                >
                  <td className="px-2 py-2 align-top text-xs tabular-nums text-ink-400">{p.id}</td>
                  <td className="whitespace-nowrap px-2 py-2 align-top font-mono text-xs font-semibold text-ink-800">
                    {p.interni_id}
                  </td>
                  <td className="px-2 py-2 align-top">
                    <div className={`font-semibold ${aktiven ? "text-fines-700" : "text-ink-900"}`}>{p.naziv}</div>
                    {p.opis && <div className="line-clamp-2 text-xs text-ink-500">{p.opis}</div>}
                  </td>
                  <td className="hidden px-2 py-2 align-top text-xs text-ink-600 sm:table-cell">
                    {druzineProgramaText(p, sifranti) || "-"}
                  </td>
                  <td className="px-2 py-2 text-right align-top tabular-nums text-ink-700">{p.stKorakov}</td>
                </tr>
              );
            })}
            {filtrirani.length === 0 && (
              <tr>
                <td colSpan={5} className="px-2 py-8 text-center text-sm text-ink-400">
                  {programi.length ? "Ni programov za izbrane filtre." : "Ni še nobenega programa."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
