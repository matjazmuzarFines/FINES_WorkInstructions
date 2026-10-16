"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { ClipboardList } from "lucide-react";
import {
  naloziKorake,
  naloziPripravo,
  naloziProgram,
  naloziSifrante,
  podsekcijaLabel,
  type Korak,
  type Priprava,
  type Program,
  type Sifranti,
  type Slika,
} from "@/lib/navodila";
import { supabaseConfigured } from "@/lib/supabase";
import { Modal } from "@/components/ui/Modal";
import { ConfigMissing, ErrorText, Loading } from "@/components/ui/Notice";

/**
 * Prikaz navodila za delavca (osnovna verzija - podrobna oblika strani bo sledila):
 * glava programa, nato koraki eden pod drugim s slikami in opisi.
 */
export function NavodiloPrikaz() {
  const params = useParams<{ id: string }>();
  const iskalni = useSearchParams();
  const id = Number(params.id);
  const [program, setProgram] = useState<Program | null>(null);
  const [koraki, setKoraki] = useState<Korak[] | null>(null);
  const [sifranti, setSifranti] = useState<Sifranti | null>(null);
  const [napaka, setNapaka] = useState<string | null>(null);
  const [povecana, setPovecana] = useState<Slika | null>(null);
  const [priprava, setPriprava] = useState<Priprava[]>([]);

  useEffect(() => {
    if (!supabaseConfigured) return;
    Promise.all([naloziProgram(id), naloziKorake(id), naloziSifrante(), naloziPripravo(id)])
      .then(([p, k, s, pr]) => {
        setPriprava(pr);
        if (!p) throw new Error("Navodilo ne obstaja ali je bilo odstranjeno.");
        setProgram(p);
        setKoraki(k);
        setSifranti(s);
      })
      .catch((e: Error) => setNapaka(e.message));
  }, [id]);

  if (!supabaseConfigured) return <ConfigMissing />;
  if (napaka) return <ErrorText className="mx-auto max-w-xl">{napaka}</ErrorText>;
  if (!program || !koraki) return <Loading />;

  const ident = iskalni.get("ident");
  const nalog = iskalni.get("nalog");
  const podsekcije = program.podsekcije
    .map((pid) => sifranti?.podsekcije.find((p) => p.id === pid))
    .filter((p) => p !== undefined)
    .map((p) => podsekcijaLabel(p, sifranti!.sekcije));

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4">
      <section className="fp-card flex items-start gap-4 border-l-4 border-l-fines-500 p-4 sm:p-6">
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-ink-800 px-2 py-0.5 font-mono text-sm font-bold text-white">{program.interni_id}</span>
            {podsekcije.map((p) => (
              <span key={p} className="rounded-full bg-fines-50 px-2 py-0.5 text-xs font-semibold text-fines-700">
                {p}
              </span>
            ))}
            {(ident || nalog) && (
              <span className="ml-auto text-sm text-ink-500">
                {nalog && (
                  <>
                    Nalog <strong className="font-mono text-ink-800">{nalog}</strong> ·{" "}
                  </>
                )}
                {ident && (
                  <>
                    Ident <strong className="font-mono text-ink-800">{ident}</strong>
                  </>
                )}
              </span>
            )}
          </div>
          <h2 className="text-2xl font-bold text-ink-900 sm:text-3xl">{program.naziv}</h2>
          {program.opis && <p className="whitespace-pre-wrap text-ink-600">{program.opis}</p>}
        </div>
        {program.koncnaUrl && (
          <button
            type="button"
            title="Povečaj sliko končnega proizvoda"
            onClick={() => setPovecana({ id: -1, korak_id: -1, pot: "", opis: "Končni proizvod", vrstni_red: 0, url: program.koncnaUrl })}
            className="w-28 shrink-0 overflow-hidden rounded-lg border border-ink-200 bg-ink-50 sm:w-40"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={program.koncnaUrl} alt={`Končni proizvod - ${program.naziv}`} className="aspect-square w-full object-contain" />
          </button>
        )}
      </section>

      {priprava.length > 0 && (
        <section className="fp-card flex flex-col gap-3 p-4 sm:p-6">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-ink-800 text-white">
              <ClipboardList className="h-5 w-5" aria-hidden />
            </span>
            <div>
              <h3 className="text-xl font-bold text-ink-900">Priprava delovnega mesta</h3>
              <p className="text-sm text-ink-500">Pred začetkom pripravi:</p>
            </div>
          </div>
          <ul className="grid gap-x-6 gap-y-1.5 sm:grid-cols-2">
            {priprava.map((p) => (
              <li key={p.id} className="flex items-start gap-2 text-base text-ink-800">
                <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-fines-500" aria-hidden />
                {p.naziv}
              </li>
            ))}
          </ul>
        </section>
      )}

      {koraki.length === 0 && <p className="py-10 text-center text-ink-400">Navodilo še nima korakov.</p>}

      {koraki.map((k, i) => (
        <section key={k.id} className="fp-card flex flex-col gap-3 p-4 sm:p-6">
          <div className="flex items-start gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-fines-500 text-lg font-bold text-white">
              {i + 1}
            </span>
            <div className="min-w-0 flex-1">
              <h3 className="text-xl font-bold text-ink-900">{k.naziv || `Korak ${i + 1}`}</h3>
              {k.opis && <p className="mt-1 whitespace-pre-wrap text-base text-ink-700">{k.opis}</p>}
            </div>
          </div>
          {k.slike.length > 0 && (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {k.slike.map((s) => (
                <figure key={s.id} className="flex flex-col gap-1">
                  <button
                    type="button"
                    title="Povečaj sliko"
                    onClick={() => setPovecana(s)}
                    className="overflow-hidden rounded-lg border border-ink-200 bg-ink-100"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={s.url} alt={s.opis ?? "Slika koraka"} className="aspect-[4/3] w-full object-contain" />
                  </button>
                  {s.opis && <figcaption className="text-sm text-ink-600">{s.opis}</figcaption>}
                </figure>
              ))}
            </div>
          )}
        </section>
      ))}

      <Modal open={!!povecana} title={povecana?.opis || "Slika"} onClose={() => setPovecana(null)} sirina="max-w-6xl">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        {povecana && <img src={povecana.url} alt={povecana.opis ?? "Slika koraka"} className="mx-auto max-h-[75vh] object-contain" />}
      </Modal>
    </div>
  );
}
