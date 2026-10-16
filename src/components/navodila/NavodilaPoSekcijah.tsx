"use client";

import { Layers } from "lucide-react";
import type { Podsekcija, Program, Sekcija, Sifranti } from "@/lib/navodila";
import { ProgramKartica } from "./ProgramKartica";

type Skupina = { podsekcija: Podsekcija | null; programi: Program[] };
type SekcijaSkupina = { sekcija: Sekcija | null; skupine: Skupina[]; stevilo: number };

/** Programi po sekcijah in podsekcijah (program z več podsekcijami je v vsaki). */
function razvrsti(programi: Program[], s: Sifranti): SekcijaSkupina[] {
  const out: SekcijaSkupina[] = [];
  for (const sekcija of s.sekcije) {
    const skupine = s.podsekcije
      .filter((p) => p.sekcija_id === sekcija.id)
      .map((p) => ({ podsekcija: p, programi: programi.filter((pr) => pr.podsekcije.includes(p.id)) }))
      .filter((g) => g.programi.length);
    if (skupine.length) out.push({ sekcija, skupine, stevilo: new Set(skupine.flatMap((g) => g.programi.map((p) => p.id))).size });
  }
  const znane = new Set(s.podsekcije.map((p) => p.id));
  const brez = programi.filter((p) => !p.podsekcije.some((id) => znane.has(id)));
  if (brez.length) out.push({ sekcija: null, skupine: [{ podsekcija: null, programi: brez }], stevilo: brez.length });
  return out;
}

const sidro = (s: Sekcija | null) => `sekcija-${s?.koda ?? "ostalo"}`;

/**
 * Navodila po sekcijah: vsaka sekcija ima svoj naslov in je vizualno ločena,
 * v njej so vrstice podsekcij - levo oznaka podsekcije, desno kartice navodil.
 */
export function NavodilaPoSekcijah({ programi, sifranti, href }: { programi: Program[]; sifranti: Sifranti; href: (p: Program) => string }) {
  const sekcije = razvrsti(programi, sifranti);

  if (!sekcije.length) return <p className="py-10 text-center text-ink-400">Ni navodil za izbrane filtre.</p>;

  return (
    <div className="flex flex-col gap-8">
      {/* hitri skok na sekcijo */}
      {sekcije.length > 1 && (
        <nav className="flex flex-wrap gap-2" aria-label="Sekcije">
          {sekcije.map((g) => (
            <a
              key={sidro(g.sekcija)}
              href={`#${sidro(g.sekcija)}`}
              title={`Pojdi na sekcijo ${g.sekcija?.naziv ?? "Ostalo"}`}
              className="flex h-10 items-center gap-2 rounded-full border border-ink-200 bg-white px-4 text-sm font-semibold text-ink-700 shadow-sm hover:border-fines-500 hover:text-fines-600"
            >
              <Layers className="h-4 w-4 text-fines-500" aria-hidden />
              {g.sekcija?.naziv ?? "Ostalo"}
              <span className="rounded-full bg-ink-100 px-2 text-xs tabular-nums text-ink-600">{g.stevilo}</span>
            </a>
          ))}
        </nav>
      )}

      {sekcije.map((g) => (
        <section key={sidro(g.sekcija)} id={sidro(g.sekcija)} className="scroll-mt-24 overflow-hidden rounded-2xl border border-ink-200 bg-ink-100/60 shadow-sm">
          {/* naslov sekcije */}
          <div className="flex items-center gap-3 border-b-4 border-fines-500 bg-ink-800 px-4 py-3 sm:px-5">
            <span className="text-xl font-extrabold uppercase tracking-wider text-white sm:text-2xl">{g.sekcija?.naziv ?? "Ostalo"}</span>
            <span className="rounded-full bg-white/10 px-2.5 py-0.5 text-sm font-semibold tabular-nums text-ink-200">
              {g.stevilo} {g.stevilo === 1 ? "navodilo" : "navodil"}
            </span>
          </div>

          <div className="flex flex-col divide-y divide-ink-200">
            {g.skupine.map((sk) => (
              <div key={sk.podsekcija?.id ?? "brez"} className="flex flex-col gap-2 p-3 sm:p-4 md:flex-row md:gap-4">
                {/* oznaka podsekcije: na telefonu naslov z oranžno črto (kot v meniju), od md naprej ozek navpičen trak */}
                <div className="flex items-center gap-2 md:hidden">
                  <span className="shrink-0 text-xs font-bold uppercase tracking-wider text-fines-600">{sk.podsekcija?.naziv ?? "Brez podsekcije"}</span>
                  <span className="text-xs tabular-nums text-ink-400">{sk.programi.length}</span>
                  <span className="h-px flex-1 bg-fines-500/40" aria-hidden />
                </div>
                <div
                  className="hidden w-9 shrink-0 items-center justify-center rounded-lg bg-fines-500 py-3 shadow-sm md:flex"
                  title={`Podsekcija ${sk.podsekcija?.naziv ?? "Brez podsekcije"} - ${sk.programi.length} navodil`}
                >
                  <span className="rotate-180 whitespace-nowrap text-xs font-bold uppercase tracking-[0.2em] text-white [writing-mode:vertical-rl]">
                    {sk.podsekcija?.naziv ?? "Brez podsekcije"}
                    <span className="ml-2 font-semibold text-white/70">{sk.programi.length}</span>
                  </span>
                </div>
                <div className="grid min-w-0 flex-1 gap-3 lg:grid-cols-2 2xl:grid-cols-3">
                  {sk.programi.map((p) => (
                    <ProgramKartica key={p.id} program={p} href={href(p)} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
