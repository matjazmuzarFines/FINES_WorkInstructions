"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { BookOpen, ChevronDown, CloudUpload, FileBox, FolderOpen, Image as ImageIcon, LayoutList, Pause, Play, Plus, RefreshCw, SplitSquareHorizontal } from "lucide-react";
import { AI_JI, naslednjiPoskus, type AiKoda, type Ocena, type TreningIndeks } from "@/lib/trening";
import { naloziIndeks, objaviTrening, shraniOceno, urlDatoteke, ustvariSliko } from "@/lib/treningApi";
import { naloziObjavljeno, zadnjaObjava } from "@/lib/treningObjava";
import { Button } from "@/components/ui/Button";
import { FilterIzbira, FilterPolje, FilterVrstica } from "@/components/ui/Filtri";
import { ErrorText, Loading, WarningText } from "@/components/ui/Notice";
import { Zavihki } from "@/components/ui/Zavihki";
import { useToast } from "@/components/ui/Toast";
import { NovModelOkno } from "./NovModelOkno";
import { Besedilo, PoskusPanel } from "./PoskusPanel";
import { PrimerjavaTabela, ocenaZa } from "./PrimerjavaTabela";
import { TreningPregled } from "./TreningPregled";
import { SlikaModela } from "./SlikaModela";
import { datumCas, napakaJson, podatki, velikost } from "./oblika";

const SPOMIN_MODEL = "wi-trening-model";

type Pogled = "pregled" | "primerjava";

/**
 * AI trening (training ground): isti 3D model obdelata GPT-6.2 Astra in Claude Fable 5.2
 * (vsak v svojem chatu v VS Code), tukaj pa izhode primerjaš drug ob drugem in jih oceniš.
 * Lokalno: vse akcije (prompt, ocena, nov model, objava). Produkcija: objavljena kopija, samo pregled.
 */
export function Trening() {
  const notify = useToast();
  const [indeks, setIndeks] = useState<TreningIndeks | null>(null);
  const [url, setUrl] = useState<{ f: (pot: string) => string }>({ f: () => "" });
  const [objavljeno, setObjavljeno] = useState<string | null>(null);
  const [objavljam, setObjavljam] = useState(false);
  const [risem, setRisem] = useState(false);
  const [pogled, setPogled] = useState<Pogled>("pregled");
  const [napaka, setNapaka] = useState<string | null>(null);
  const [osvezujem, setOsvezujem] = useState(false);
  const [modelId, setModelId] = useState<string | null>(null);
  const [izbira, setIzbira] = useState<Partial<Record<AiKoda, string>>>({});
  const [dolzine, setDolzine] = useState<Partial<Record<AiKoda, number | null>>>({});
  const [novModel, setNovModel] = useState(false);
  const videi = useRef<Partial<Record<AiKoda, HTMLVideoElement | null>>>({});

  const nalozi = useCallback(async () => {
    setOsvezujem(true);
    try {
      const r = await naloziIndeks();
      if (!r.indeks.omogoceno && r.indeks.produkcija) {
        const o = await naloziObjavljeno();
        setIndeks(o.indeks);
        setUrl({ f: (pot) => o.urlji[pot] ?? "" });
        setObjavljeno(o.objavljeno);
      } else {
        setIndeks(r.indeks);
        setUrl({ f: (pot) => urlDatoteke(pot, r.zeton) });
        setObjavljeno(await zadnjaObjava());
      }
      setNapaka(null);
    } catch (e) {
      setNapaka((e as Error).message);
    } finally {
      setOsvezujem(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- začetno nalaganje z diska
    nalozi();
  }, [nalozi]);

  if (napaka && !indeks) return <ErrorText>{napaka}</ErrorText>;
  if (!indeks) return <Loading />;
  if (!indeks.omogoceno) return <WarningText>{indeks.razlog}</WarningText>;

  const modeli = indeks.modeli;
  const lokalno = indeks.vir === "lokalno";
  const shranjen = typeof window !== "undefined" ? window.localStorage.getItem(SPOMIN_MODEL) : null;
  const model =
    modeli.find((m) => m.id === modelId) ?? modeli.find((m) => m.id === shranjen) ?? modeli[modeli.length - 1] ?? null;

  function izberiModel(id: string) {
    window.localStorage.setItem(SPOMIN_MODEL, id);
    setModelId(id);
    setIzbira({});
    setDolzine({});
  }

  async function izrisiSliko(id: string) {
    setRisem(true);
    try {
      await ustvariSliko(id);
      notify("success", "Sličica modela je izrisana iz STEP.");
      await nalozi();
    } catch (e) {
      notify("error", (e as Error).message);
    } finally {
      setRisem(false);
    }
  }

  async function objavi() {
    setObjavljam(true);
    try {
      const r = await objaviTrening();
      notify("success", `Objavljeno: ${r.modelov} modelov, ${r.poskusov} poskusov, naloženih datotek ${r.datotek}.`);
      setObjavljeno(await zadnjaObjava());
    } catch (e) {
      notify("error", (e as Error).message);
    } finally {
      setObjavljam(false);
    }
  }

  const izbran = (ai: AiKoda) => {
    const p = model?.poskusi[ai] ?? [];
    return p.find((x) => x.poskus === izbira[ai]) ?? p[p.length - 1] ?? null;
  };

  async function oceni(ai: AiKoda, o: Ocena) {
    const p = izbran(ai);
    if (!model || !p) return;
    try {
      await shraniOceno(model.id, ai, p.poskus, o);
      notify("success", "Ocena je shranjena.");
      await nalozi();
    } catch (e) {
      notify("error", (e as Error).message);
    }
  }

  const vsiVidei = () => AI_JI.map((a) => videi.current[a.koda]).filter((v): v is HTMLVideoElement => !!v);
  function predvajajOba() {
    for (const v of vsiVidei()) {
      v.currentTime = 0;
      v.play().catch(() => {});
    }
  }
  const ustaviOba = () => vsiVidei().forEach((v) => v.pause());
  const obaVidea = AI_JI.every((a) => izbran(a.koda)?.video);

  const info = model ? podatki(model.info) : null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-[min(100%,18rem)] flex-1">
          <h1 className="text-xl font-bold text-ink-900">AI trening</h1>
          <p className="text-sm text-ink-500">
            Isti 3D model obdelata Astra in Fable, tukaj primerjaš video navodila in jih oceniš.{" "}
            {lokalno ? "Lokalni strežnik - podatki z diska." : "Produkcija - objavljena kopija, samo pregled."}{" "}
            {objavljeno ? `Zadnja objava: ${datumCas(objavljeno)}.` : lokalno ? "Na produkciji še ni objave." : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <Button
            variant="sync"
            icon={RefreshCw}
            hint={lokalno ? "Ponovno preberi mapo trening z diska" : "Ponovno preberi objavljene podatke"}
            onClick={nalozi}
            disabled={osvezujem}
          >
            {osvezujem ? "Berem ..." : "Osveži"}
          </Button>
          {lokalno && (
            <>
              <Button variant="sync" icon={CloudUpload} hint="Objavi treninge in videe na produkcijo" onClick={objavi} disabled={objavljam}>
                {objavljam ? "Objavljam ..." : "Objavi na produkcijo"}
              </Button>
              <Button variant="success" icon={Plus} hint="Dodaj nov 3D model za trening" onClick={() => setNovModel(true)}>
                Nov model
              </Button>
            </>
          )}
        </div>
      </div>

      {napaka && <ErrorText>{napaka}</ErrorText>}

      <div>
        <Zavihki<Pogled>
          label="Pogled AI treninga"
          value={pogled}
          onChange={setPogled}
          zavihki={[
            { koda: "pregled", label: "Pregled", icon: LayoutList, hint: "Pregled vseh treningov in poskusov" },
            { koda: "primerjava", label: "Primerjava", icon: SplitSquareHorizontal, hint: "Primerjaj poskusa Astre in Fable" },
          ]}
        />
        <div className="fp-card flex min-w-0 flex-col gap-4 rounded-tl-none p-3 sm:p-4">
          {pogled === "pregled" ? (
            <>
              <TreningPregled
                modeli={modeli}
                url={url.f}
                onOdpri={(id) => {
                  izberiModel(id);
                  setPogled("primerjava");
                }}
              />
              <details className="group rounded-lg border border-ink-200 p-3">
                <summary
                  className="flex cursor-pointer list-none items-center gap-2 text-sm font-bold text-ink-800"
                  title="Pokaži skupno znanje, ki ga bereta oba AI-ja"
                >
                  <BookOpen className="h-4 w-4 text-fines-500" aria-hidden />
                  Skupno znanje (trening/ZNANJE.md)
                  <ChevronDown className="ml-auto h-4 w-4 text-ink-500 transition-transform group-open:rotate-180" aria-hidden />
                </summary>
                <p className="mt-2 text-xs text-ink-500">
                  Potrjena pravila in spoznanja, ki jih bereta oba AI-ja. Predloge AI-ja najdeš v zavihku Spoznanja; dobre prenesi v ZNANJE.md.
                </p>
                <div className="mt-2">
                  {indeks.znanje ? <Besedilo>{indeks.znanje}</Besedilo> : <WarningText>Manjka trening/ZNANJE.md.</WarningText>}
                </div>
              </details>
            </>
          ) : !model ? (
            <div className="flex flex-col items-center gap-3 p-8 text-center">
              <FileBox className="h-12 w-12 text-fines-500" aria-hidden />
              <h2 className="text-xl font-bold text-ink-900">Še ni modelov</h2>
              {lokalno ? (
                <>
                  <p className="text-sm text-ink-600">
                    Dodaj prvi 3D model (STEP). Aplikacija ustvari mapo{" "}
                    <code className="rounded bg-ink-100 px-1">trening/modeli/&lt;id&gt;/</code>, nato v oba chata prilepiš prompt in
                    primerjaš rezultate.
                  </p>
                  <Button variant="success" icon={Plus} hint="Dodaj nov 3D model za trening" onClick={() => setNovModel(true)}>
                    Nov model
                  </Button>
                </>
              ) : (
                <p className="text-sm text-ink-600">Na produkcijo še ni objavljen noben trening.</p>
              )}
            </div>
          ) : (
            <>
              <FilterVrstica>
                <FilterIzbira
                  label="Model"
                  value={model.id}
                  options={modeli.map((m) => ({ value: m.id, label: podatki(m.info)?.naziv ?? m.id }))}
                  onChange={izberiModel}
                  hint="Izberi 3D model za primerjavo"
                />
                {obaVidea && (
                  <FilterPolje label="Videa">
                    <div className="flex flex-wrap gap-2">
                      <Button icon={Play} hint="Predvajaj oba videa hkrati od začetka" onClick={predvajajOba}>
                        Predvajaj oba
                      </Button>
                      <Button variant="neutral" icon={Pause} hint="Ustavi predvajanje obeh videov" onClick={ustaviOba}>
                        Ustavi oba
                      </Button>
                    </div>
                  </FilterPolje>
                )}
              </FilterVrstica>

              <section className="flex flex-wrap gap-4 rounded-lg border border-ink-200 bg-ink-50 p-3" aria-label="Model">
                <div className="flex w-full max-w-[16rem] flex-col gap-2">
                  <SlikaModela src={model.slika ? url.f(model.slika) || null : null} naziv={info?.naziv ?? model.id} velikost="velika" />
                  {lokalno && (
                    <Button icon={ImageIcon} hint="Izriši sličico modela iz STEP datoteke" onClick={() => izrisiSliko(model.id)} disabled={risem}>
                      {risem ? "Rišem ..." : model.slika ? "Nova sličica" : "Sličica iz STEP"}
                    </Button>
                  )}
                </div>
                <div className="min-w-[min(100%,18rem)] flex-1">
                  <h2 className="text-lg font-bold text-ink-900">{info?.naziv ?? model.id}</h2>
                  <p className="font-mono text-xs text-ink-400" title="Mapa modela v projektu">
                    trening/modeli/{model.id}/
                    {info?.zahteva_id ? ` · zahteva #${info.zahteva_id}` : ""}
                    {info?.oddal ? ` · oddal ${info.oddal}` : ""}
                  </p>
                  {info?.opis && <p className="mt-2 whitespace-pre-wrap text-sm text-ink-700">{info.opis}</p>}
                  {napakaJson(model.info) && <ErrorText className="mt-2">model.json: {napakaJson(model.info)}</ErrorText>}
                </div>
                {lokalno && (
                  <div className="min-w-[min(100%,16rem)]">
                    <div className="mb-1 flex items-center gap-1 text-xs font-semibold text-ink-600">
                      <FolderOpen className="h-4 w-4" aria-hidden /> Vhod (vhod/)
                    </div>
                    {model.vhod.length === 0 ? (
                      <WarningText>V vhod/ ni STEP datoteke - dodaj jo v mapo.</WarningText>
                    ) : (
                      <ul className="flex flex-col gap-1 text-sm">
                        {model.vhod.map((d) => (
                          <li key={d.pot} className="flex justify-between gap-3" title={`Spremenjeno ${datumCas(d.cas)}`}>
                            <span className="min-w-0 truncate font-mono text-xs">{d.ime}</span>
                            <span className="shrink-0 text-xs tabular-nums text-ink-500">{velikost(d.velikost)}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </section>

              <div className="grid items-start gap-4 lg:grid-cols-2">
                {AI_JI.map((a) => (
                  <PoskusPanel
                    key={`${model.id}/${a.koda}`}
                    ai={a.koda}
                    modelId={model.id}
                    poskusi={model.poskusi[a.koda]}
                    izbran={izbran(a.koda)}
                    onIzberi={(p) => {
                      setIzbira((s) => ({ ...s, [a.koda]: p }));
                      setDolzine((s) => ({ ...s, [a.koda]: null }));
                    }}
                    naslednji={naslednjiPoskus(model.poskusi[a.koda])}
                    ocena={ocenaZa(model.ocene, a.koda, izbran(a.koda))}
                    onShraniOceno={(o) => oceni(a.koda, o)}
                    url={url.f}
                    samoBranje={!lokalno}
                    videoRef={(el) => {
                      videi.current[a.koda] = el;
                    }}
                    onDolzina={(s) => setDolzine((d) => ({ ...d, [a.koda]: s }))}
                  />
                ))}
              </div>

              <PrimerjavaTabela
                strani={
                  Object.fromEntries(
                    AI_JI.map((a) => [
                      a.koda,
                      { poskus: izbran(a.koda), ocena: ocenaZa(model.ocene, a.koda, izbran(a.koda)), dolzina: dolzine[a.koda] ?? null },
                    ]),
                  ) as Record<AiKoda, { poskus: ReturnType<typeof izbran>; ocena: Ocena | undefined; dolzina: number | null }>
                }
              />
            </>
          )}
        </div>
      </div>

      <NovModelOkno
        open={novModel}
        onClose={() => setNovModel(false)}
        onUstvarjen={async (id) => {
          setNovModel(false);
          notify("success", `Model ${id} je dodan v trening/modeli/${id}/.`);
          await nalozi();
          izberiModel(id);
        }}
      />
    </div>
  );
}
