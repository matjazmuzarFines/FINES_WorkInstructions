"use client";

import { useId, useRef, useState, type RefObject } from "react";
import { Clock, Save } from "lucide-react";
import { KRITERIJI, povprecje, type KriterijKoda, type Ocena } from "@/lib/trening";
import { Button } from "@/components/ui/Button";
import { WarningText } from "@/components/ui/Notice";
import { useNeshranjeno } from "@/lib/neshranjeno";
import { datumCas } from "./oblika";

/** 83.4 s -> "1:23" */
function oznakaCasa(s: number) {
  const t = Math.floor(s);
  return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
}

/** Ocena poskusa: kriteriji 1-5 in komentar. Shrani se v trening/modeli/<model>/ocene.json. */
export function OcenaObrazec({
  ocena,
  onShrani,
  video,
}: {
  ocena: Ocena | undefined;
  onShrani: (o: Ocena) => Promise<void>;
  /** Video ob obrazcu: omogoči vstavljanje trenutnega časa v komentar. */
  video?: RefObject<HTMLVideoElement | null>;
}) {
  const [kriteriji, setKriteriji] = useState<Ocena["kriteriji"]>(ocena?.kriteriji ?? {});
  const [komentar, setKomentar] = useState(ocena?.komentar ?? "");
  const [delam, setDelam] = useState(false);

  const spremenjeno =
    komentar !== (ocena?.komentar ?? "") ||
    KRITERIJI.some((k) => kriteriji[k.koda] !== ocena?.kriteriji?.[k.koda]);
  const pov = povprecje({ kriteriji, komentar, datum: "" });
  const polje = useRef<HTMLTextAreaElement>(null);
  const idPolja = useId();
  useNeshranjeno(spremenjeno);

  function vstaviCas() {
    const v = video?.current;
    const ta = polje.current;
    if (!v || !ta) return;
    const oznaka = `[${oznakaCasa(v.currentTime)}] `;
    const zac = ta.selectionStart ?? komentar.length;
    const kon = ta.selectionEnd ?? komentar.length;
    const pred = komentar.slice(0, zac);
    const presledek = pred && !/\s$/.test(pred) ? "\n" : "";
    setKomentar(pred + presledek + oznaka + komentar.slice(kon));
    const poz = zac + presledek.length + oznaka.length;
    requestAnimationFrame(() => {
      ta.focus();
      ta.setSelectionRange(poz, poz);
    });
  }

  function nastavi(k: KriterijKoda, v: number) {
    setKriteriji((s) => ({ ...s, [k]: s[k] === v ? undefined : v }));
  }

  async function shrani() {
    setDelam(true);
    try {
      await onShrani({ kriteriji, komentar, datum: "" });
    } finally {
      setDelam(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {KRITERIJI.map((k) => (
        <div key={k.koda} className="flex flex-wrap items-center justify-between gap-2">
          <div className="min-w-[min(100%,12rem)] flex-1">
            <div className="text-sm font-semibold text-ink-800">{k.naziv}</div>
            <div className="text-xs text-ink-500">{k.opis}</div>
          </div>
          <div className="flex gap-1" role="radiogroup" aria-label={k.naziv}>
            {[1, 2, 3, 4, 5].map((v) => {
              const izbran = kriteriji[k.koda] === v;
              return (
                <button
                  key={v}
                  type="button"
                  role="radio"
                  aria-checked={izbran}
                  title={izbran ? `Odstrani oceno ${v} za ${k.naziv}` : `Oceni ${k.naziv} z ${v}`}
                  onClick={() => nastavi(k.koda, v)}
                  className={`h-10 w-10 rounded-lg border text-sm font-bold transition-colors ${
                    izbran
                      ? "border-fines-500 bg-fines-500 text-white"
                      : "border-ink-200 bg-white text-ink-600 hover:bg-ink-100"
                  }`}
                >
                  {v}
                </button>
              );
            })}
          </div>
        </div>
      ))}
      <div className="flex flex-col gap-1 text-xs font-semibold text-ink-600">
        <span className="flex flex-wrap items-center justify-between gap-2">
          <label htmlFor={idPolja}>Komentar</label>
          {video && (
            <Button
              icon={Clock}
              hint="Vstavi trenutni čas videa v komentar"
              onClick={vstaviCas}
              onMouseDown={(e) => e.preventDefault()}
              className="!h-8 !px-3 !text-xs"
            >
              Vstavi čas
            </Button>
          )}
        </span>
        <textarea
          ref={polje}
          id={idPolja}
          value={komentar}
          onChange={(e) => setKomentar(e.target.value)}
          rows={video ? 8 : 4}
          title="Kaj je dobro, kaj je narobe, kaj popraviti"
          placeholder="Kaj je dobro, kaj je narobe, kaj naj popravi v naslednjem poskusu ..."
          className="rounded-lg border border-ink-200 p-3 text-sm font-normal text-ink-800 focus:border-fines-500 focus:outline-none focus:ring-2 focus:ring-fines-100"
        />
      </div>
      {spremenjeno && <WarningText>Neshranjene spremembe ocene.</WarningText>}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm text-ink-600" title="Povprečje vpisanih kriterijev">
          Povprečje: <b className="text-ink-900">{pov === null ? "-" : pov.toFixed(1).replace(".", ",")}</b>
          {ocena?.datum && <span className="ml-2 text-xs text-ink-400">shranjeno {datumCas(ocena.datum)}</span>}
        </span>
        <Button variant="success" icon={Save} hint="Shrani oceno tega poskusa" onClick={shrani} disabled={delam || !spremenjeno}>
          {delam ? "Shranjujem ..." : "Shrani oceno"}
        </Button>
      </div>
    </div>
  );
}
