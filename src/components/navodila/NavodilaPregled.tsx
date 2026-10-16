"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { RotateCcw, ScanBarcode, SearchX } from "lucide-react";
import { naloziPrograme, naloziSifrante, podsekcijaLabel, poisciNavodila, type Program, type Sifranti, type Zadetek } from "@/lib/navodila";
import { supabaseConfigured } from "@/lib/supabase";
import { ujemaIskanje } from "@/lib/iskanje";
import { Button } from "@/components/ui/Button";
import { FilterIskanje, FilterPolje, FilterVrstica } from "@/components/ui/Filtri";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { ConfigMissing, ErrorText, Loading } from "@/components/ui/Notice";
import { NavodilaPoSekcijah } from "./NavodilaPoSekcijah";

/** Povezava do navodila z ozadjem skeniranja (ident, nalog). */
export function navodiloHref(programId: number, z?: Pick<Zadetek, "ident" | "nalog"> | null) {
  const p = new URLSearchParams();
  if (z?.ident) p.set("ident", z.ident);
  if (z?.nalog) p.set("nalog", z.nalog);
  const q = p.toString();
  return `/navodila/${programId}${q ? `?${q}` : ""}`;
}

/**
 * Proizvodnja - Navodila.
 * - Po skeniranju (?koda=...): na vrhu nalog / ident, spodaj navodila tega identa po sekcijah;
 *   če je navodilo eno samo, se odpre takoj.
 * - Brez kode: vsa navodila s filtri, razvrščena po sekcijah in podsekcijah.
 */
export function NavodilaPregled() {
  const router = useRouter();
  const koda = useSearchParams().get("koda")?.trim() || null;
  const [programi, setProgrami] = useState<Program[] | null>(null);
  const [sifranti, setSifranti] = useState<Sifranti | null>(null);
  const [zadetek, setZadetek] = useState<{ koda: string; z: Zadetek } | null>(null);
  const [napaka, setNapaka] = useState<string | null>(null);
  const [iskanje, setIskanje] = useState("");
  const [podsekcije, setPodsekcije] = useState<string[]>([]);

  useEffect(() => {
    if (!supabaseConfigured) return;
    let preklicano = false;
    const iskanjeKode = koda ? poisciNavodila(koda) : Promise.resolve(null);
    Promise.all([naloziPrograme(), naloziSifrante(), iskanjeKode])
      .then(([p, s, z]) => {
        if (preklicano) return;
        if (koda && z && z.programi.length === 1) {
          router.replace(navodiloHref(z.programi[0].id, z));
          return;
        }
        setProgrami(p);
        setSifranti(s);
        setZadetek(koda && z ? { koda, z } : null);
      })
      .catch((e: Error) => !preklicano && setNapaka(e.message));
    return () => {
      preklicano = true;
    };
  }, [koda, router]);

  if (!supabaseConfigured) return <ConfigMissing />;
  if (napaka) return <ErrorText>{napaka}</ErrorText>;
  const z = koda && zadetek?.koda === koda ? zadetek.z : null;
  if (!programi || !sifranti || (koda && !z)) return <Loading />;

  const label = (id: number) => {
    const p = sifranti.podsekcije.find((x) => x.id === id);
    return p ? podsekcijaLabel(p, sifranti.sekcije) : "";
  };
  const osnova = z ? z.programi : programi;
  const vidni = osnova.filter(
    (p) =>
      ujemaIskanje([p.interni_id, p.naziv, p.opis ?? ""].join(" "), iskanje) &&
      (!podsekcije.length || p.podsekcije.some((id) => podsekcije.includes(label(id)))),
  );

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-5">
      {z ? (
        <ZadetekGlava z={z} />
      ) : (
        <div className="flex flex-col gap-3">
          <div className="min-w-[min(100%,18rem)] flex-1">
            <h2 className="text-xl font-bold text-ink-900">Navodila</h2>
            <p className="text-sm text-ink-500">Vsa navodila za montažo in proizvodnjo ({vidni.length})</p>
          </div>
          <div className="fp-card p-3 sm:p-4">
            <FilterVrstica>
              <FilterIskanje value={iskanje} onChange={setIskanje} placeholder="ID, ime ali opis ..." hint="Išči navodilo po ID, imenu ali opisu" />
              <div className="w-full sm:w-72">
                <MultiSelect
                  label="Podsekcije"
                  options={sifranti.podsekcije.map((p) => label(p.id))}
                  value={podsekcije}
                  onChange={setPodsekcije}
                  hint="Prikaži navodila izbranih podsekcij"
                />
              </div>
              {(iskanje || podsekcije.length > 0) && (
                <FilterPolje>
                  <Button
                    hint="Ponastavi vse filtre navodil"
                    variant="neutral"
                    icon={RotateCcw}
                    onClick={() => {
                      setIskanje("");
                      setPodsekcije([]);
                    }}
                  >
                    Ponastavi
                  </Button>
                </FilterPolje>
              )}
            </FilterVrstica>
          </div>
        </div>
      )}

      {z && z.programi.length === 0 ? (
        <NiNavodil z={z} />
      ) : (
        <NavodilaPoSekcijah programi={vidni} sifranti={sifranti} href={(p) => navodiloHref(p.id, z)} />
      )}
    </div>
  );
}

/** Temen pas z rezultatom skeniranja: naziv, nalog, ident, gumb za nov nalog. */
function ZadetekGlava({ z }: { z: Zadetek }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-ink-900 px-5 py-4 text-white shadow-lg">
      <div className="min-w-0">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-fines-400">
          {z.programi.length ? "Izberi svoje navodilo" : "Skeniran nalog"}
        </p>
        <p className="mt-1 text-lg font-bold sm:text-xl">
          {z.naziv ?? z.ident ?? z.koda}
          {z.programi.length > 0 && <span className="ml-2 text-sm font-normal text-ink-300">{z.programi.length} navodil</span>}
        </p>
      </div>
      <div className="flex flex-wrap gap-2 font-mono text-xs">
        {z.nalog && <span className="rounded-lg bg-white/10 px-2.5 py-1.5">Nalog {z.nalog}</span>}
        {z.ident && <span className="rounded-lg bg-white/10 px-2.5 py-1.5">Ident {z.ident}</span>}
        <Link
          href="/"
          title="Nazaj na skeniranje novega naloga"
          className="flex items-center gap-1.5 rounded-lg bg-fines-500 px-3 py-1.5 font-sans font-semibold hover:bg-fines-600"
        >
          <ScanBarcode className="h-4 w-4" aria-hidden /> Nov nalog
        </Link>
      </div>
    </div>
  );
}

function NiNavodil({ z }: { z: Zadetek }) {
  return (
    <div className="mx-auto flex w-full max-w-2xl items-start gap-4 rounded-2xl border border-warn-400/60 bg-warn-50 p-4 shadow-sm sm:p-5">
      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-warn-400 text-ink-900">
        <SearchX className="h-6 w-6" aria-hidden />
      </div>
      <div className="min-w-0 flex-1">
        <p className="font-bold text-ink-900">Navodila niso najdena</p>
        <p className="mt-0.5 text-sm text-warn-700">
          {z.ident ? (
            <>
              Za ident <strong className="font-mono">{z.ident}</strong>
              {z.naziv ? ` (${z.naziv})` : ""} še ni pripravljenih navodil. Obvesti vodjo.
            </>
          ) : (
            <>
              Koda <strong className="font-mono">{z.koda}</strong> ni znan delovni nalog ali ident. Skeniraj ponovno.
            </>
          )}
        </p>
      </div>
    </div>
  );
}
