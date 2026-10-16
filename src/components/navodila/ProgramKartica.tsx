"use client";

import Link from "next/link";
import { ArrowRight, ListOrdered, Package } from "lucide-react";
import type { Program } from "@/lib/navodila";

/** Kartica programa navodil: besedilo levo, končna slika proizvoda desno. */
export function ProgramKartica({ program, href }: { program: Program; href: string }) {
  return (
    <Link
      href={href}
      title={`Odpri navodilo ${program.interni_id}`}
      className="fp-card group flex min-h-36 items-stretch gap-3 p-3 transition-all hover:-translate-y-0.5 hover:border-fines-500 hover:shadow-md sm:p-4"
    >
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-md bg-ink-800 px-2 py-0.5 font-mono text-xs font-bold text-white">{program.interni_id}</span>
          <span className="flex items-center gap-1 text-xs text-ink-500" title="Število korakov navodila">
            <ListOrdered className="h-4 w-4" aria-hidden />
            {program.stKorakov} korakov
          </span>
        </div>
        <div className="flex-1">
          <div className="text-lg font-bold leading-tight text-ink-900 group-hover:text-fines-600">{program.naziv}</div>
          {program.opis && <p className="mt-1 line-clamp-2 text-sm text-ink-600">{program.opis}</p>}
        </div>
        <span className="flex items-center gap-1 text-sm font-semibold text-fines-500">
          Odpri navodilo
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" aria-hidden />
        </span>
      </div>
      <div
        className="flex w-28 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-ink-200 bg-ink-50 sm:w-32"
        title={program.koncnaUrl ? "Končni proizvod" : "Ni slike končnega proizvoda"}
      >
        {program.koncnaUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={program.koncnaUrl} alt={`Končni proizvod - ${program.naziv}`} className="h-full max-h-40 w-full object-contain" />
        ) : (
          <Package className="h-10 w-10 text-ink-300" aria-hidden />
        )}
      </div>
    </Link>
  );
}
