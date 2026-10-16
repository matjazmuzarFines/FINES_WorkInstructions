"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Barcode, BookOpenCheck, CornerDownLeft, Loader2, ScanLine } from "lucide-react";
import { supabaseConfigured } from "@/lib/supabase";
import { ConfigMissing } from "@/components/ui/Notice";

const KORAKI = [
  { ikona: Barcode, naslov: "Skeniraj", opis: "črtno kodo na delovnem nalogu" },
  { ikona: BookOpenCheck, naslov: "Odpre se", opis: "navodilo za tvoj izdelek" },
  { ikona: ScanLine, naslov: "Sledi", opis: "korakom in slikam" },
];

/**
 * Domača stran: skeniranje črtne kode delovnega naloga (ali identa).
 * Po skeniranju se odpre stran Navodila (/proizvodnja/navodila?koda=...): eno navodilo se odpre
 * samo, več navodil je za izbiro po sekcijah.
 * Polje je vedno pripravljeno: tipke čitalnika gredo v polje, tudi če fokus ni na njem.
 */
export function Skeniranje() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [koda, setKoda] = useState("");
  const [iscem, setIscem] = useState(false);
  const [aktivno, setAktivno] = useState(true);

  // Čitalnik deluje kot tipkovnica: znak izven polja preusmeri v polje skeniranja.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = document.activeElement;
      if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement || el instanceof HTMLSelectElement) return;
      if (document.querySelector('[role="dialog"]')) return;
      if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) inputRef.current?.focus();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function isci(e?: FormEvent) {
    e?.preventDefault();
    const vnos = koda.trim();
    if (!vnos || iscem) return;
    setIscem(true);
    router.push(`/proizvodnja/navodila?koda=${encodeURIComponent(vnos)}`);
  }

  if (!supabaseConfigured) return <ConfigMissing />;


  return (
    <div className="relative -mx-3 -my-4 flex min-h-[calc(100dvh-6.5rem)] flex-col items-center overflow-hidden px-4 py-8 sm:-mx-6 sm:-my-6 sm:py-14">
      {/* ozadje: topel oranžen sij in rahla mreža */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_70%_50%_at_50%_0%,rgb(202_80_16/0.14),transparent_70%)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.35] [background-image:linear-gradient(var(--color-ink-200)_1px,transparent_1px),linear-gradient(90deg,var(--color-ink-200)_1px,transparent_1px)] [background-size:48px_48px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_30%,black,transparent)]"
      />

      <div className="relative flex w-full max-w-2xl flex-col items-center gap-8">
        {/* naslov */}
        <div className="flex flex-col items-center gap-3 text-center">
          <span className="rounded-full border border-fines-200 bg-white/80 px-3 py-1 text-xs font-bold uppercase tracking-[0.2em] text-fines-600 shadow-sm">
            Navodila za delo
          </span>
          <h2 className="text-3xl font-extrabold tracking-tight text-ink-900 sm:text-5xl">
            Skeniraj <span className="text-fines-500">delovni nalog</span>
          </h2>
          <p className="max-w-md text-base text-ink-500 sm:text-lg">Navodilo za montažo ali proizvodnjo se odpre samo.</p>
        </div>

        {/* polje za skeniranje */}
        <form onSubmit={isci} className="w-full max-w-2xl">
          <div
            className={`group relative flex items-center gap-4 rounded-3xl border-2 bg-white p-3 pl-4 shadow-xl shadow-ink-900/5 transition-all sm:p-4 sm:pl-5 ${
              aktivno ? "border-fines-500 ring-8 ring-fines-500/10" : "border-ink-200"
            }`}
            onClick={() => inputRef.current?.focus()}
          >
            {/* ikona čitalnika z lasersko črto */}
            <div className="relative flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-ink-900 text-white sm:h-16 sm:w-16">
              {iscem ? (
                <Loader2 className="h-7 w-7 animate-spin text-fines-400" aria-hidden />
              ) : (
                <>
                  <Barcode className="h-8 w-8 sm:h-9 sm:w-9" aria-hidden />
                  {aktivno && <span className="wi-laser absolute inset-x-1.5 top-1/2 h-0.5 rounded-full bg-fines-400 shadow-[0_0_10px_2px_var(--color-fines-500)]" />}
                </>
              )}
            </div>

            <input
              ref={inputRef}
              autoFocus
              value={koda}
              onChange={(e) => setKoda(e.target.value)}
              onFocus={() => setAktivno(true)}
              onBlur={() => setAktivno(false)}
              placeholder={aktivno ? "Čakam na skeniranje ..." : "Klikni za skeniranje"}
              title="Skeniraj ali vpiši številko naloga / ident in pritisni Enter"
              aria-label="Številka delovnega naloga ali ident"
              autoComplete="off"
              spellCheck={false}
              className="h-12 min-w-0 flex-1 bg-transparent font-mono text-xl font-semibold tracking-wider text-ink-900 placeholder:font-sans placeholder:text-base placeholder:font-normal placeholder:tracking-normal placeholder:text-ink-400 focus:outline-none sm:h-14 sm:text-3xl sm:placeholder:text-xl"
            />

            {koda && !iscem && (
              <button
                type="submit"
                title="Poišči navodila za vpisano kodo"
                className="flex h-12 shrink-0 items-center gap-2 rounded-2xl bg-fines-500 px-4 font-bold text-white shadow-md transition-colors hover:bg-fines-600 sm:h-14 sm:px-6"
              >
                <span className="hidden sm:inline">Odpri</span>
                <ArrowRight className="h-5 w-5" aria-hidden />
              </button>
            )}
          </div>

          <div className="mt-3 flex items-center justify-center gap-2 text-sm text-ink-500">
            <span className={`h-2 w-2 rounded-full ${aktivno ? "animate-pulse bg-ok-500" : "bg-ink-300"}`} aria-hidden />
            {iscem ? (
              "Iščem navodila ..."
            ) : aktivno ? (
              <>
                Pripravljen · ali vpiši kodo in pritisni
                <kbd className="inline-flex items-center gap-1 rounded-md border border-ink-200 bg-white px-1.5 py-0.5 text-xs font-semibold text-ink-600 shadow-sm">
                  Enter <CornerDownLeft className="h-3 w-3" aria-hidden />
                </kbd>
              </>
            ) : (
              "Polje ni aktivno - klikni nanj ali kar skeniraj"
            )}
          </div>
        </form>

        {/* kako deluje */}
        {!iscem && (
          <ol className="grid w-full max-w-2xl grid-cols-3 gap-2 sm:gap-4">
            {KORAKI.map((k, i) => (
              <li key={k.naslov} className="flex flex-col items-center gap-2 rounded-2xl bg-white/70 p-3 text-center ring-1 ring-ink-200/70 backdrop-blur sm:p-4">
                <div className="relative">
                  <k.ikona className="h-6 w-6 text-fines-500 sm:h-7 sm:w-7" aria-hidden />
                  <span className="absolute -right-3 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-ink-900 text-[10px] font-bold text-white">
                    {i + 1}
                  </span>
                </div>
                <div>
                  <p className="text-sm font-bold text-ink-900">{k.naslov}</p>
                  <p className="text-xs leading-snug text-ink-500">{k.opis}</p>
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
