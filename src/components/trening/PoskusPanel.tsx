"use client";

import { useState, type CSSProperties, type Ref } from "react";
import { Boxes, ClipboardCopy, FileText, Files, Lightbulb, ListOrdered, Star, VideoOff } from "lucide-react";
import {
  AI_JI,
  zagonskiPrompt,
  type AiKoda,
  type Del,
  type Korak,
  type Ocena,
  type Poskus,
} from "@/lib/trening";
import { urlDatoteke } from "@/lib/treningApi";
import { Button } from "@/components/ui/Button";
import { FilterIzbira } from "@/components/ui/Filtri";
import { ErrorText, WarningText } from "@/components/ui/Notice";
import { useToast } from "@/components/ui/Toast";
import { Zavihki } from "@/components/ui/Zavihki";
import { OcenaObrazec } from "./OcenaObrazec";
import { BARVA_AI, STATUS, casGeneracije, datumCas, napakaJson, podatki, trajanje, velikost } from "./oblika";

type Pogled = "povzetek" | "spoznanja" | "koraki" | "deli" | "datoteke" | "ocena";

/** Ena stran primerjave: izbran poskus enega AI-ja (video, podatki, ocena). */
export function PoskusPanel({
  ai,
  modelId,
  poskusi,
  izbran,
  onIzberi,
  naslednji,
  ocena,
  onShraniOceno,
  zeton,
  videoRef,
  onDolzina,
}: {
  ai: AiKoda;
  modelId: string;
  poskusi: Poskus[];
  izbran: Poskus | null;
  onIzberi: (poskus: string) => void;
  naslednji: string;
  ocena: Ocena | undefined;
  onShraniOceno: (o: Ocena) => Promise<void>;
  zeton: string;
  videoRef: Ref<HTMLVideoElement>;
  onDolzina: (s: number | null) => void;
}) {
  const notify = useToast();
  const [pogled, setPogled] = useState<Pogled>("povzetek");
  const info = AI_JI.find((a) => a.koda === ai)!;
  const barva = BARVA_AI[ai];

  async function kopirajPrompt() {
    await navigator.clipboard.writeText(zagonskiPrompt(ai, modelId, naslednji));
    notify("success", `Prompt za ${info.naziv}, poskus ${naslednji} je kopiran.`);
  }

  const meta = izbran ? podatki(izbran.meta) : null;
  const deli = izbran ? podatki(izbran.deli) : null;
  const koraki = izbran ? podatki(izbran.koraki) : null;
  const status = meta?.status ? STATUS[meta.status] ?? { label: meta.status, cls: "bg-ink-100 text-ink-700" } : null;

  return (
    <section className={`fp-card flex min-w-0 flex-col gap-3 border-t-4 p-3 sm:p-4 ${barva.trak}`} aria-label={info.naziv}>
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex min-w-[min(100%,14rem)] flex-1 items-center gap-3">
          <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-lg font-bold ${barva.znacka}`} title={info.naziv}>
            {barva.crka}
          </span>
          <div className="min-w-0">
            <h2 className="truncate text-lg font-bold text-ink-900">{info.naziv}</h2>
            <p className="truncate text-xs text-ink-500">{info.orodje}</p>
          </div>
        </div>
        {poskusi.length > 0 && (
          <FilterIzbira
            label="Poskus"
            value={izbran?.poskus ?? ""}
            options={[...poskusi].reverse().map((p) => ({ value: p.poskus, label: `Poskus ${p.poskus}` }))}
            onChange={onIzberi}
            hint={`Izberi poskus ${info.naziv}`}
          />
        )}
        <Button icon={ClipboardCopy} hint={`Kopiraj prompt za poskus ${naslednji}`} onClick={kopirajPrompt}>
          Prompt {naslednji}
        </Button>
      </div>

      {!izbran ? (
        <div className="rounded-lg border border-dashed border-ink-300 bg-ink-50 p-6 text-center text-sm text-ink-600">
          <p className="font-semibold text-ink-800">Še ni poskusa.</p>
          <p className="mt-1">
            Kopiraj prompt in ga prilepi v {info.orodje}. Izhodi se pojavijo tukaj po kliku Osveži.
          </p>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {status && <span className={`rounded-full px-2.5 py-1 font-semibold ${status.cls}`}>{status.label}</span>}
            {meta?.ai_model && <span className="rounded-full bg-ink-100 px-2.5 py-1 text-ink-700" title="Model, ki je izdelal poskus">{meta.ai_model}</span>}
            {meta?.konec && <span className="text-ink-500">{datumCas(meta.konec)}</span>}
            {casGeneracije(meta?.zacetek, meta?.konec) !== null && (
              <span className="text-ink-500" title="Čas od začetka do konca poskusa">
                · trajalo {trajanje(casGeneracije(meta?.zacetek, meta?.konec))}
              </span>
            )}
          </div>

          <div className="overflow-hidden rounded-lg bg-ink-900">
            {izbran.video ? (
              <video
                key={izbran.video}
                ref={videoRef}
                src={urlDatoteke(izbran.video, zeton)}
                poster={izbran.predogled ? urlDatoteke(izbran.predogled, zeton) : undefined}
                controls
                playsInline
                preload="metadata"
                title={`Video navodila - ${info.naziv}, poskus ${izbran.poskus}`}
                onLoadedMetadata={(e) => onDolzina(e.currentTarget.duration)}
                className="aspect-video w-full"
              />
            ) : izbran.predogled ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={urlDatoteke(izbran.predogled, zeton)}
                alt={`Predogled - ${info.naziv}`}
                title="Predogled (videa še ni)"
                className="aspect-video w-full object-contain"
              />
            ) : (
              <div className="flex aspect-video flex-col items-center justify-center gap-2 text-ink-400">
                <VideoOff className="h-10 w-10" aria-hidden />
                <span className="text-sm">Ni videa (video.mp4) ne predogleda</span>
              </div>
            )}
          </div>

          <div className="grid grid-cols-3 gap-2 text-center">
            <Kazalnik naslov="Deli" vrednost={deli?.length} hint="Število delov v deli.json" />
            <Kazalnik naslov="Koraki" vrednost={koraki?.length} hint="Število korakov v koraki.json" />
            <Kazalnik naslov="Datoteke" vrednost={izbran.datoteke.length} hint="Število datotek v mapi poskusa" />
          </div>

          <div>
            <Zavihki<Pogled>
              label="Podatki poskusa"
              value={pogled}
              onChange={setPogled}
              zavihki={[
                { koda: "povzetek", label: "Poročilo", icon: FileText, hint: "Pokaži poročilo in povzetek poskusa" },
                { koda: "spoznanja", label: "Spoznanja", icon: Lightbulb, hint: "Predlogi AI za skupno znanje" },
                { koda: "koraki", label: "Koraki", icon: ListOrdered, hint: "Pokaži montažne korake iz koraki.json" },
                { koda: "deli", label: "Deli", icon: Boxes, hint: "Pokaži inventuro delov iz deli.json" },
                { koda: "datoteke", label: "Datoteke", icon: Files, hint: "Pokaži vse datoteke poskusa" },
                { koda: "ocena", label: "Ocena", icon: Star, hint: "Oceni ta poskus po kriterijih" },
              ]}
            />
            <div className="rounded-b-xl rounded-tr-xl border border-ink-200 bg-white p-3">
              {pogled === "povzetek" && <Povzetek poskus={izbran} />}
              {pogled === "spoznanja" &&
                (izbran.spoznanja ? (
                  <Besedilo>{izbran.spoznanja}</Besedilo>
                ) : (
                  <WarningText>Manjka spoznanja.md.</WarningText>
                ))}
              {pogled === "koraki" && <Koraki napaka={napakaJson(izbran.koraki)} koraki={koraki} />}
              {pogled === "deli" && <Deli napaka={napakaJson(izbran.deli)} deli={deli} />}
              {pogled === "datoteke" && <SeznamDatotek poskus={izbran} zeton={zeton} />}
              {pogled === "ocena" && <OcenaObrazec key={`${ai}/${izbran.poskus}`} ocena={ocena} onShrani={onShraniOceno} />}
            </div>
          </div>
        </>
      )}
    </section>
  );
}

function Kazalnik({ naslov, vrednost, hint }: { naslov: string; vrednost: number | undefined; hint: string }) {
  return (
    <div className="rounded-lg bg-ink-50 px-2 py-2" title={hint}>
      <div className="text-xs font-semibold text-ink-500">{naslov}</div>
      <div className="text-xl font-bold text-ink-900">{vrednost ?? "-"}</div>
    </div>
  );
}

function Povzetek({ poskus }: { poskus: Poskus }) {
  const meta = podatki(poskus.meta);
  const napaka = napakaJson(poskus.meta);
  return (
    <div className="flex flex-col gap-3 text-sm">
      {napaka && <ErrorText>meta.json: {napaka}</ErrorText>}
      {!poskus.meta && <WarningText>Manjka meta.json.</WarningText>}
      {meta?.povzetek && <p className="text-ink-800">{meta.povzetek}</p>}
      {!!meta?.orodja?.length && (
        <div>
          <div className="text-xs font-semibold text-ink-600">Orodja</div>
          <div className="mt-1 flex flex-wrap gap-1">
            {meta.orodja.map((o) => (
              <span key={o} className="rounded-full bg-ink-100 px-2 py-0.5 text-xs text-ink-700">{o}</span>
            ))}
          </div>
        </div>
      )}
      {!!meta?.tezave?.length && (
        <WarningText>
          <div className="font-semibold">Težave in neznanke</div>
          <ul className="mt-1 list-disc pl-5 font-normal">
            {meta.tezave.map((t, i) => <li key={i}>{t}</li>)}
          </ul>
        </WarningText>
      )}
      {poskus.porocilo ? (
        <Besedilo>{poskus.porocilo}</Besedilo>
      ) : (
        <WarningText>Manjka porocilo.md.</WarningText>
      )}
    </div>
  );
}

/** Markdown kot navadno besedilo (brez dodatne knjižnice). */
export function Besedilo({ children }: { children: string }) {
  return (
    <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap break-words rounded-lg bg-ink-50 p-3 font-sans text-sm text-ink-800">
      {children}
    </pre>
  );
}

function Koraki({ koraki, napaka }: { koraki: Korak[] | null; napaka: string | null }) {
  if (napaka) return <ErrorText>koraki.json: {napaka}</ErrorText>;
  if (!koraki?.length) return <p className="text-sm text-ink-500">Ni korakov (koraki.json).</p>;
  return (
    <ol className="flex max-h-[32rem] flex-col gap-2 overflow-auto">
      {koraki.map((k, i) => (
        <li key={i} className="rounded-lg border border-ink-200 p-3 text-sm">
          <div className="flex items-start gap-2">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-fines-500 text-xs font-bold text-white">
              {k.st ?? i + 1}
            </span>
            <div className="min-w-0 flex-1">
              <div className="font-semibold text-ink-900">{k.naslov ?? "(brez naslova)"}</div>
              {k.opis && <p className="mt-0.5 text-ink-700">{k.opis}</p>}
              <div className="mt-1 flex flex-wrap gap-1 text-xs">
                {k.gibanje?.tip && <span className="rounded-full bg-ink-100 px-2 py-0.5 text-ink-700">{k.gibanje.tip}</span>}
                {typeof k.gibanje?.trajanje_s === "number" && (
                  <span className="rounded-full bg-ink-100 px-2 py-0.5 text-ink-700">{k.gibanje.trajanje_s} s</span>
                )}
                {(k.deli ?? []).map((d) => (
                  <span key={d} className="rounded-full bg-fines-50 px-2 py-0.5 font-mono text-fines-700">{d}</span>
                ))}
              </div>
              {!!k.opozorila?.length && (
                <ul className="mt-1 list-disc pl-5 text-xs text-warn-700">
                  {k.opozorila.map((o, j) => <li key={j}>{o}</li>)}
                </ul>
              )}
              {k.potrditev && <p className="mt-1 text-xs font-semibold text-warn-700">{k.potrditev}</p>}
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}

const mm = (n: number) => n.toLocaleString("sl-SI", { maximumFractionDigits: 1 });

function Deli({ deli, napaka }: { deli: Del[] | null; napaka: string | null }) {
  if (napaka) return <ErrorText>deli.json: {napaka}</ErrorText>;
  if (!deli?.length) return <p className="text-sm text-ink-500">Ni delov (deli.json).</p>;
  return (
    <div className="max-h-[32rem] overflow-auto rounded-lg" style={{ "--fp-thead-top": "0px" } as CSSProperties}>
      <table className="w-full min-w-[28rem] text-sm">
        <thead className="fp-thead">
          <tr>
            <th className="px-3 py-2">ID</th>
            <th className="px-3 py-2">Ime</th>
            <th className="px-3 py-2">Tip</th>
            <th className="px-3 py-2 text-right">Velikost (mm)</th>
          </tr>
        </thead>
        <tbody>
          {deli.map((d, i) => {
            const b = d.bbox_mm;
            const dim = b?.min?.length === 3 && b?.max?.length === 3 ? b.max.map((v, j) => mm(v - b.min[j])).join(" × ") : "";
            return (
              <tr key={`${d.id}-${i}`} className="border-b border-ink-100" title={d.opomba}>
                <td className="px-3 py-1.5 font-mono text-xs">{d.id}</td>
                <td className="px-3 py-1.5">{d.ime ?? ""}{d.kolicina && d.kolicina > 1 ? ` × ${d.kolicina}` : ""}</td>
                <td className="px-3 py-1.5 text-ink-600">{d.tip ?? ""}</td>
                <td className="px-3 py-1.5 text-right text-ink-600">{dim}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function SeznamDatotek({ poskus, zeton }: { poskus: Poskus; zeton: string }) {
  if (!poskus.datoteke.length) return <p className="text-sm text-ink-500">Mapa je prazna.</p>;
  return (
    <ul className="max-h-[32rem] divide-y divide-ink-100 overflow-auto text-sm">
      {poskus.datoteke.map((d) => (
        <li key={d.pot} className="flex items-center justify-between gap-3 py-1.5">
          <a
            href={urlDatoteke(d.pot, zeton)}
            target="_blank"
            rel="noreferrer"
            title={`Odpri ${d.ime} v novem zavihku`}
            className="min-w-0 truncate font-mono text-xs text-fines-600 hover:underline"
          >
            {d.ime}
          </a>
          <span className="shrink-0 text-xs text-ink-500">{velikost(d.velikost)}</span>
        </li>
      ))}
    </ul>
  );
}
