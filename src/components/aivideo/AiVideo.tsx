"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import {
  Ban,
  Box,
  CheckCircle2,
  FileSpreadsheet,
  FolderInput,
  Image as ImageIcon,
  Pencil,
  RefreshCw,
  Send,
  UploadCloud,
  X,
  type LucideIcon,
} from "lucide-react";
import {
  MAX_DATOTEKA,
  STATUSI,
  naloziPorabo,
  naloziZahteve,
  nastaviStatus,
  oddajZahtevo,
  shraniProracun,
  urlDatotekeZahteve,
  type Poraba,
  type VrstaDatoteke,
  type Zahteva,
} from "@/lib/aiZahteve";
import { jeLokalno, zahtevaVTrening } from "@/lib/treningApi";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ErrorText, Loading, WarningText } from "@/components/ui/Notice";
import { SortTh, TabelaOkvir, useRazvrscanje } from "@/components/ui/Tabela";
import { FilterIskanje, FilterIzbira, FilterPolje, FilterPreklopnik, FilterVrstica } from "@/components/ui/Filtri";
import { Izvoz } from "@/components/ui/Izvoz";
import { ujemaIskanje } from "@/lib/iskanje";
import { danesIso, prenesiXlsx } from "@/lib/excel";
import { useToast } from "@/components/ui/Toast";
import { datumCas, velikost } from "@/components/trening/oblika";

const POLJE =
  "h-10 w-full rounded-lg border border-ink-200 px-3 text-sm font-normal focus:border-fines-500 focus:outline-none focus:ring-2 focus:ring-fines-100";

const VRSTE: { vrsta: VrstaDatoteke; naslov: string; opis: string; accept: string; icon: LucideIcon; hint: string }[] = [
  { vrsta: "step", naslov: "3D model (STEP)", opis: ".step / .stp", accept: ".step,.stp,.STEP,.STP", icon: Box, hint: "Dodaj STEP model sestava" },
  {
    vrsta: "kosovnica",
    naslov: "Kosovnica (Excel)",
    opis: ".xlsx / .xls / .csv",
    accept: ".xlsx,.xls,.csv",
    icon: FileSpreadsheet,
    hint: "Dodaj kosovnico sestava v Excelu",
  },
  { vrsta: "slika", naslov: "Slike", opis: "fotografije, skice", accept: "image/*", icon: ImageIcon, hint: "Dodaj slike ali skice sestava" },
];

const usd = (v: number) => `${v.toLocaleString("sl-SI", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} $`;
const tisoc = (v: number) => v.toLocaleString("sl-SI");

/**
 * AI video creation: razvojnik odda STEP, kosovnico, slike in pojasnila; zahteva gre v vrsto.
 * Admin jo na lokalnem strežniku prenese v AI trening in generira video (zdaj z naročnino v VS Code,
 * kasneje prek API kreditov - poraba je prikazana zgoraj desno).
 */
export function AiVideo() {
  const notify = useToast();
  const [zahteve, setZahteve] = useState<Zahteva[] | null>(null);
  const [poraba, setPoraba] = useState<Poraba | null>(null);
  const [lokalno, setLokalno] = useState(false);
  const [napaka, setNapaka] = useState<string | null>(null);
  const [osvezujem, setOsvezujem] = useState(false);
  const [delam, setDelam] = useState<number | null>(null);
  const [zavrni, setZavrni] = useState<Zahteva | null>(null);

  const nalozi = useCallback(async () => {
    setOsvezujem(true);
    try {
      const [z, p, l] = await Promise.all([naloziZahteve(), naloziPorabo(), jeLokalno()]);
      setZahteve(z);
      setPoraba(p);
      setLokalno(l);
      setNapaka(null);
    } catch (e) {
      setNapaka((e as Error).message);
    } finally {
      setOsvezujem(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- začetno nalaganje iz baze
    nalozi();
  }, [nalozi]);

  async function vTrening(z: Zahteva) {
    setDelam(z.id);
    try {
      const r = await zahtevaVTrening(z.id);
      notify("success", `Zahteva #${z.id} je v treningu kot model ${r.koda} (${r.datotek} datotek).`);
      await nalozi();
    } catch (e) {
      notify("error", (e as Error).message);
    } finally {
      setDelam(null);
    }
  }

  async function status(z: Zahteva, s: Zahteva["status"], opomba?: string) {
    setDelam(z.id);
    try {
      await nastaviStatus(z.id, s, opomba);
      notify("success", `Zahteva #${z.id}: ${STATUSI[s].label.toLowerCase()}.`);
      await nalozi();
    } catch (e) {
      notify("error", (e as Error).message);
    } finally {
      setDelam(null);
    }
  }

  async function prenesi(pot: string) {
    try {
      window.open(await urlDatotekeZahteve(pot), "_blank", "noopener");
    } catch (e) {
      notify("error", (e as Error).message);
    }
  }

  if (napaka && !zahteve) return <ErrorText>{napaka}</ErrorText>;
  if (!zahteve || !poraba) return <Loading />;

  const cakajo = zahteve.filter((z) => z.status === "oddano").length;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-[min(100%,18rem)] flex-1">
          <h1 className="text-xl font-bold text-ink-900">AI video creation</h1>
          <p className="text-sm text-ink-500">
            Naloži 3D model, kosovnico, slike in pojasnila - AI iz njih pripravi video navodila za montažo.
          </p>
        </div>
        <Button variant="sync" icon={RefreshCw} hint="Ponovno preberi zahteve in porabo" onClick={nalozi} disabled={osvezujem}>
          {osvezujem ? "Berem ..." : "Osveži"}
        </Button>
      </div>

      {napaka && <ErrorText>{napaka}</ErrorText>}

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <NovaZahteva
          poraba={poraba}
          onOddano={async (id) => {
            notify("success", `Zahteva #${id} je oddana.`);
            await nalozi();
          }}
        />
        <div className="flex flex-col gap-4">
          <PorabaKartica poraba={poraba} onShranjeno={nalozi} />
          <section className="fp-card p-3 text-sm text-ink-700 sm:p-4" aria-label="Postopek">
            <h2 className="mb-2 text-base font-bold text-ink-900">Kako poteka</h2>
            <ol className="flex list-decimal flex-col gap-1 pl-5">
              <li>Razvojnik odda zahtevo z datotekami in pojasnili.</li>
              <li>Zahteva čaka v vrsti (značka v meniju).</li>
              <li>Admin jo na lokalnem strežniku prenese v AI trening in generira video.</li>
              <li>Rezultat se objavi na produkcijo (AI trening) in zahteva se označi kot končana.</li>
            </ol>
          </section>
        </div>
      </div>

      <section className="fp-card flex min-w-0 flex-col gap-3 p-3 sm:p-4" aria-label="Zahteve">
        <div>
          <h2 className="text-lg font-bold text-ink-900">Zahteve</h2>
          <p className="text-sm text-ink-500">
            {zahteve.length} zahtev · {cakajo} čaka na obdelavo.
            {!lokalno && " Prenos v trening je mogoč samo na lokalnem strežniku."}
          </p>
        </div>
        <ZahteveTabela
          zahteve={zahteve}
          lokalno={lokalno}
          delam={delam}
          onVTrening={vTrening}
          onKoncano={(z) => status(z, "koncano")}
          onZavrni={setZavrni}
          onPrenesi={prenesi}
        />
      </section>

      <ZavrniOkno
        zahteva={zavrni}
        onClose={() => setZavrni(null)}
        onPotrdi={async (opomba) => {
          const z = zavrni!;
          setZavrni(null);
          await status(z, "zavrnjeno", opomba);
        }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------

type StatusFilter = "vse" | Zahteva["status"];
type ZKljuc = "id" | "naziv" | "oddal" | "oddano" | "datoteke" | "status";
const RED_STATUSA: Record<Zahteva["status"], number> = { oddano: 0, v_delu: 1, koncano: 2, zavrnjeno: 3 };

/** Standardna tabela zahtev: filtri (iskanje, status, oddal) z izvozom, razvrščanje po vseh stolpcih s podatki. */
function ZahteveTabela({
  zahteve,
  lokalno,
  delam,
  onVTrening,
  onKoncano,
  onZavrni,
  onPrenesi,
}: {
  zahteve: Zahteva[];
  lokalno: boolean;
  delam: number | null;
  onVTrening: (z: Zahteva) => void;
  onKoncano: (z: Zahteva) => void;
  onZavrni: (z: Zahteva) => void;
  onPrenesi: (pot: string) => void;
}) {
  const [iskanje, setIskanje] = useState("");
  const [status, setStatus] = useState<StatusFilter>("vse");
  const [oddal, setOddal] = useState("vsi");

  const sort = useRazvrscanje<Zahteva, ZKljuc>({
    id: (z) => z.id,
    naziv: (z) => z.naziv,
    oddal: (z) => z.oddal,
    oddano: (z) => z.created_at,
    datoteke: (z) => z.datoteke.length,
    status: (z) => RED_STATUSA[z.status],
  });

  const oddajniki = [...new Set(zahteve.map((z) => z.oddal))].sort((a, b) => a.localeCompare(b, "sl"));
  const poIskanju = zahteve.filter(
    (z) =>
      ujemaIskanje(`${z.id} ${z.naziv} ${z.opis ?? ""} ${z.model_koda ?? ""} ${z.datoteke.map((d) => d.ime).join(" ")}`, iskanje) &&
      (oddal === "vsi" || z.oddal === oddal),
  );
  const vrstice = sort.razvrsti(poIskanju.filter((z) => status === "vse" || z.status === status));
  const imaFilter = !!iskanje || status !== "vse" || oddal !== "vsi";

  function izvoziExcel() {
    return prenesiXlsx(
      [
        {
          ime: "Zahteve",
          vrstice: vrstice.map((z) => ({
            "#": z.id,
            Zahteva: z.naziv,
            Pojasnila: z.opis ?? "",
            Oddal: z.oddal,
            Oddano: datumCas(z.created_at),
            Datoteke: z.datoteke.map((d) => d.ime).join(", "),
            Status: STATUSI[z.status].label,
            Način: z.nacin === "api" ? "API krediti" : "lokalno",
            "Model v treningu": z.model_koda ?? "",
            Opomba: z.opomba ?? "",
          })),
        },
      ],
      `AI_video_zahteve_${danesIso()}`,
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <FilterVrstica>
        <FilterIskanje value={iskanje} onChange={setIskanje} placeholder="Naziv, pojasnila, datoteka" hint="Išči po nazivu, pojasnilih in datotekah" />
        <FilterPreklopnik<StatusFilter>
          label="Status"
          value={status}
          onChange={setStatus}
          options={[
            { value: "vse", label: "Vse", hint: "Pokaži zahteve v vseh statusih", stevilo: poIskanju.length },
            ...(Object.keys(STATUSI) as Zahteva["status"][]).map((s) => ({
              value: s,
              label: STATUSI[s].label,
              hint: `Pokaži samo zahteve s statusom ${STATUSI[s].label.toLowerCase()}`,
              stevilo: poIskanju.filter((z) => z.status === s).length,
            })),
          ]}
        />
        <FilterIzbira
          label="Oddal"
          value={oddal}
          options={[{ value: "vsi", label: "Vsi" }, ...oddajniki.map((o) => ({ value: o, label: o }))]}
          onChange={setOddal}
          hint="Pokaži zahteve izbranega razvojnika"
        />
        {imaFilter && (
          <FilterPolje>
            <Button
              variant="neutral"
              hint="Ponastavi iskanje, status in oddajnika"
              onClick={() => {
                setIskanje("");
                setStatus("vse");
                setOddal("vsi");
              }}
            >
              Ponastavi filtre
            </Button>
          </FilterPolje>
        )}
        <Izvoz
          className="ml-auto"
          spomin="ai-video-zahteve"
          formati={[{ koda: "xlsx", label: "Excel (.xlsx)", hint: "Prenesi prikazane zahteve v Excel", akcija: izvoziExcel }]}
        />
      </FilterVrstica>

      <TabelaOkvir>
        <table className="w-full min-w-[60rem] text-sm">
          <thead className="fp-thead">
            <tr>
              <SortTh sort={sort} kljuc="id" desno hint="Razvrsti po številki zahteve">
                #
              </SortTh>
              <SortTh sort={sort} kljuc="naziv">
                Zahteva
              </SortTh>
              <SortTh sort={sort} kljuc="oddal">
                Oddal
              </SortTh>
              <SortTh sort={sort} kljuc="oddano">
                Oddano
              </SortTh>
              <SortTh sort={sort} kljuc="datoteke" hint="Razvrsti po številu datotek">
                Datoteke
              </SortTh>
              <SortTh sort={sort} kljuc="status" className="text-center">
                Status
              </SortTh>
              <th className="px-2 py-2 text-right">Akcije</th>
            </tr>
          </thead>
          <tbody>
            {vrstice.map((z) => {
              const odprta = z.status === "oddano" || z.status === "v_delu";
              return (
                <tr key={z.id} className="border-b border-ink-100 align-top hover:bg-ink-50">
                  <td className="px-2 py-1.5 text-right font-mono text-xs tabular-nums text-ink-500">{z.id}</td>
                  <td className="max-w-[22rem] px-2 py-1.5">
                    <p className="font-semibold text-ink-900">{z.naziv}</p>
                    {z.opis && (
                      <p className="line-clamp-3 whitespace-pre-wrap text-xs text-ink-600" title={z.opis}>
                        {z.opis}
                      </p>
                    )}
                    {z.model_koda && <p className="mt-1 font-mono text-xs text-ink-400">trening/modeli/{z.model_koda}/</p>}
                    {z.opomba && <p className="mt-1 text-xs text-nok-600">Opomba: {z.opomba}</p>}
                  </td>
                  <td className="px-2 py-1.5 text-xs text-ink-600">{z.oddal}</td>
                  <td className="whitespace-nowrap px-2 py-1.5 text-xs text-ink-600">{datumCas(z.created_at)}</td>
                  <td className="px-2 py-1.5">
                    <ul className="flex flex-col gap-0.5 text-xs">
                      {z.datoteke.map((d) => (
                        <li key={d.id} className="flex items-baseline gap-1">
                          <button
                            type="button"
                            title={`Prenesi ${d.ime}`}
                            onClick={() => onPrenesi(d.pot)}
                            className="max-w-[14rem] truncate text-left text-fines-600 hover:underline"
                          >
                            {d.ime}
                          </button>
                          {d.velikost !== null && <span className="shrink-0 tabular-nums text-ink-400">{velikost(d.velikost)}</span>}
                        </li>
                      ))}
                    </ul>
                  </td>
                  <td className="px-2 py-1.5 text-center">
                    <span
                      className={`whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-bold ${STATUSI[z.status].cls}`}
                      title={z.nacin === "api" ? "Generiranje prek API kreditov" : "Generiranje lokalno (naročnina v VS Code)"}
                    >
                      {STATUSI[z.status].label}
                    </span>
                  </td>
                  <td className="px-2 py-1.5">
                    <div className="flex flex-wrap justify-end gap-2">
                      {lokalno && z.status === "oddano" && !z.model_koda && (
                        <Button icon={FolderInput} hint="Prenesi datoteke v nov model AI treninga" onClick={() => onVTrening(z)} disabled={delam === z.id}>
                          V trening
                        </Button>
                      )}
                      {odprta && (
                        <>
                          <Button variant="success" icon={CheckCircle2} hint="Označi zahtevo kot končano" onClick={() => onKoncano(z)} disabled={delam === z.id}>
                            Končano
                          </Button>
                          <Button variant="danger" icon={Ban} hint="Zavrni zahtevo z obrazložitvijo" onClick={() => onZavrni(z)} disabled={delam === z.id}>
                            Zavrni
                          </Button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
            {vrstice.length === 0 && (
              <tr>
                <td colSpan={7} className="px-2 py-8 text-center text-sm text-ink-400">
                  {zahteve.length ? "Ni zahtev za izbrane filtre." : "Še ni zahtev."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </TabelaOkvir>
    </div>
  );
}

// ---------------------------------------------------------------------

function NovaZahteva({ poraba, onOddano }: { poraba: Poraba; onOddano: (id: number) => Promise<void> }) {
  const [naziv, setNaziv] = useState("");
  const [opis, setOpis] = useState("");
  const [datoteke, setDatoteke] = useState<{ vrsta: VrstaDatoteke; file: File }[]>([]);
  const [napredek, setNapredek] = useState<string | null>(null);
  const [napaka, setNapaka] = useState<string | null>(null);

  function dodaj(vrsta: VrstaDatoteke, files: FileList | null) {
    if (!files) return;
    const nove = Array.from(files);
    const prevelike = nove.filter((f) => f.size > MAX_DATOTEKA);
    setNapaka(prevelike.length ? `Prevelike datoteke (največ 50 MB): ${prevelike.map((f) => f.name).join(", ")}` : null);
    setDatoteke((d) => [
      ...d,
      ...nove.filter((f) => f.size <= MAX_DATOTEKA && !d.some((x) => x.file.name === f.name && x.vrsta === vrsta)).map((file) => ({ vrsta, file })),
    ]);
  }

  async function poslji(e: FormEvent) {
    e.preventDefault();
    if (!datoteke.some((d) => d.vrsta === "step")) {
      setNapaka("Dodaj vsaj en 3D model (STEP).");
      return;
    }
    setNapaka(null);
    setNapredek("Oddajam ...");
    try {
      const id = await oddajZahtevo(naziv.trim(), opis.trim(), datoteke, (n, vse) => setNapredek(`Nalagam datoteke ${n}/${vse} ...`));
      setNaziv("");
      setOpis("");
      setDatoteke([]);
      await onOddano(id);
    } catch (err) {
      setNapaka((err as Error).message);
    } finally {
      setNapredek(null);
    }
  }

  const skupaj = datoteke.reduce((s, d) => s + d.file.size, 0);

  return (
    <section className="fp-card p-3 sm:p-4" aria-label="Nova zahteva">
      <h2 className="mb-3 text-lg font-bold text-ink-900">Nova zahteva</h2>
      <form onSubmit={poslji} className="flex flex-col gap-3">
        <label className="flex flex-col gap-1 text-xs font-semibold text-ink-600">
          Naziv sestava
          <input required value={naziv} onChange={(e) => setNaziv(e.target.value)} title="Naziv sestava, npr. Voziček delovni mali" className={POLJE} />
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold text-ink-600">
          Pojasnila za AI
          <textarea
            value={opis}
            onChange={(e) => setOpis(e.target.value)}
            rows={4}
            title="Posebnosti sestava, zaporedje, polizdelki, spoji"
            placeholder="Kaj je posebnega: kateri sklopi so polizdelki (zvarjeni), zaporedje montaže, vijaki, ki jih ni v modelu, na kaj naj bo monter pozoren ..."
            className="rounded-lg border border-ink-200 p-3 text-sm font-normal focus:border-fines-500 focus:outline-none focus:ring-2 focus:ring-fines-100"
          />
        </label>

        <div className="grid gap-2 sm:grid-cols-3">
          {VRSTE.map((v) => (
            <PoljeDatotek key={v.vrsta} {...v} stevilo={datoteke.filter((d) => d.vrsta === v.vrsta).length} onFiles={(f) => dodaj(v.vrsta, f)} />
          ))}
        </div>

        {datoteke.length > 0 && (
          <ul className="divide-y divide-ink-100 rounded-lg border border-ink-200 text-sm">
            {datoteke.map((d) => (
              <li key={`${d.vrsta}/${d.file.name}`} className="flex items-center justify-between gap-2 px-3 py-1.5">
                <span className="min-w-0 truncate">
                  <span className="mr-2 rounded bg-ink-100 px-1.5 py-0.5 text-xs font-bold text-ink-600">{d.vrsta}</span>
                  {d.file.name}
                </span>
                <span className="flex shrink-0 items-center gap-2 text-xs text-ink-500">
                  {velikost(d.file.size)}
                  <button
                    type="button"
                    title={`Odstrani ${d.file.name} s seznama`}
                    onClick={() => setDatoteke((x) => x.filter((y) => y !== d))}
                    className="rounded p-1 text-nok-500 hover:bg-nok-50"
                  >
                    <X className="h-4 w-4" aria-hidden />
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}

        <OcenaGeneriranja poraba={poraba} />

        {napaka && <ErrorText>{napaka}</ErrorText>}
        <div className="flex flex-wrap items-center justify-end gap-3">
          {datoteke.length > 0 && <span className="text-xs text-ink-500">Skupaj {velikost(skupaj)}</span>}
          <Button type="submit" variant="success" icon={Send} hint="Oddaj zahtevo in naloži datoteke" disabled={!!napredek || !naziv.trim()}>
            {napredek ?? "Oddaj zahtevo"}
          </Button>
        </div>
      </form>
    </section>
  );
}

function PoljeDatotek({
  naslov,
  opis,
  accept,
  icon: Icon,
  hint,
  stevilo,
  onFiles,
}: {
  naslov: string;
  opis: string;
  accept: string;
  icon: LucideIcon;
  hint: string;
  stevilo: number;
  onFiles: (f: FileList | null) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [nad, setNad] = useState(false);
  return (
    <>
      <button
        type="button"
        title={hint}
        onClick={() => input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setNad(true);
        }}
        onDragLeave={() => setNad(false)}
        onDrop={(e) => {
          e.preventDefault();
          setNad(false);
          onFiles(e.dataTransfer.files);
        }}
        className={`relative flex min-h-20 flex-col items-center justify-center gap-1 rounded-xl border-2 px-3 py-3 text-center text-sm transition-colors ${
          nad
            ? "border-solid border-fines-500 bg-fines-50"
            : stevilo
              ? "border-solid border-ok-500 bg-ok-50"
              : "border-dashed border-ink-300 bg-ink-100 hover:border-ink-400"
        }`}
      >
        {stevilo > 0 && <CheckCircle2 className="absolute right-2 top-2 h-4 w-4 text-ok-500" aria-hidden />}
        <Icon className={`h-6 w-6 ${nad ? "text-fines-500" : stevilo ? "text-ok-600" : "text-ink-400"}`} aria-hidden />
        <span className="font-semibold text-ink-800">{naslov}</span>
        <span className="text-xs text-ink-500">{stevilo ? `${stevilo} dodanih` : opis}</span>
      </button>
      <input
        ref={input}
        type="file"
        multiple
        accept={accept}
        hidden
        onChange={(e) => {
          onFiles(e.target.files);
          e.target.value = "";
        }}
      />
    </>
  );
}

/** Kako bo zahteva generirana: prek API kreditov (ko je vklopljeno in je dovolj kreditov) ali lokalno. */
function OcenaGeneriranja({ poraba }: { poraba: Poraba }) {
  const ostane = poraba.proracun.mesecni_usd - poraba.porabljeno;
  if (!poraba.proracun.api_vklopljen) {
    return (
      <div className="flex items-start gap-2 rounded-lg bg-ink-50 px-3 py-2 text-sm text-ink-700">
        <UploadCloud className="mt-0.5 h-4 w-4 shrink-0 text-ink-500" aria-hidden />
        <span>
          Generiranje bo <strong>lokalno</strong>: datoteke se naložijo, admin dobi obvestilo in video pripravi v VS Code. Generiranje prek API
          kreditov še ni vklopljeno.
        </span>
      </div>
    );
  }
  return ostane > 0 ? (
    <div className="flex items-start gap-2 rounded-lg bg-ok-50 px-3 py-2 text-sm text-ok-600">
      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <span>Na voljo je še {usd(ostane)} API kreditov - zahteva gre v generiranje prek API.</span>
    </div>
  ) : (
    <WarningText>API krediti za to obdobje so porabljeni - zahteva bo generirana lokalno.</WarningText>
  );
}

// ---------------------------------------------------------------------

/** Poraba API kreditov v tekočem obdobju - kot "Usage" v Claude Code (vrstica + obnova). */
function PorabaKartica({ poraba, onShranjeno }: { poraba: Poraba; onShranjeno: () => Promise<void> }) {
  const notify = useToast();
  const [urejam, setUrejam] = useState(false);
  const [mesecni, setMesecni] = useState(String(poraba.proracun.mesecni_usd));
  const [dan, setDan] = useState(String(poraba.proracun.dan_obnove));
  const p = poraba.proracun;
  const delez = p.mesecni_usd > 0 ? Math.min(poraba.porabljeno / p.mesecni_usd, 1) : 0;

  async function shrani(e: FormEvent) {
    e.preventDefault();
    try {
      await shraniProracun({ ...p, mesecni_usd: Number(mesecni.replace(",", ".")) || 0, dan_obnove: Number(dan) || 1 });
      notify("success", "Proračun je shranjen.");
      setUrejam(false);
      await onShranjeno();
    } catch (err) {
      notify("error", (err as Error).message);
    }
  }

  return (
    <section className="fp-card flex flex-col gap-3 p-3 sm:p-4" aria-label="Poraba API kreditov">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="text-base font-bold text-ink-900">Poraba API kreditov</h2>
          <p className="text-xs text-ink-500">Mesečni krediti naročnine (Claude API), obdobje od {poraba.od.toLocaleDateString("sl-SI")}</p>
        </div>
        <span
          className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold ${p.api_vklopljen ? "bg-ok-50 text-ok-600" : "bg-ink-100 text-ink-600"}`}
          title={p.api_vklopljen ? "Generiranje prek API je vklopljeno" : "Generiranje prek API še ni vklopljeno"}
        >
          {p.api_vklopljen ? "API vklopljen" : "API izklopljen"}
        </span>
      </div>

      <div title={`Porabljeno ${usd(poraba.porabljeno)} od ${usd(p.mesecni_usd)}`}>
        <div className="mb-1 flex items-baseline justify-between text-sm">
          <span className="font-semibold text-ink-800">Mesec</span>
          <span className="font-bold text-ink-900">{Math.round(delez * 100)} %</span>
        </div>
        <div className="h-2.5 overflow-hidden rounded-full bg-ink-100" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(delez * 100)}>
          <div className={`h-full rounded-full ${delez >= 0.9 ? "bg-nok-500" : "bg-fines-500"}`} style={{ width: `${delez * 100}%` }} />
        </div>
        <div className="mt-1 flex justify-between text-xs text-ink-500">
          <span>
            {usd(poraba.porabljeno)} / {usd(p.mesecni_usd)}
          </span>
          <span>Obnova {poraba.obnova.toLocaleDateString("sl-SI")}</span>
        </div>
      </div>

      <dl className="grid grid-cols-3 gap-2 text-center text-xs">
        <div className="rounded-lg bg-ink-50 p-2" title="Število klicev API v tem obdobju">
          <dt className="text-ink-500">Klici</dt>
          <dd className="font-bold text-ink-900">{tisoc(poraba.zahtevkov)}</dd>
        </div>
        <div className="rounded-lg bg-ink-50 p-2" title="Vhodni žetoni v tem obdobju">
          <dt className="text-ink-500">Vhodni žetoni</dt>
          <dd className="font-bold text-ink-900">{tisoc(poraba.vhodni)}</dd>
        </div>
        <div className="rounded-lg bg-ink-50 p-2" title="Izhodni žetoni v tem obdobju">
          <dt className="text-ink-500">Izhodni žetoni</dt>
          <dd className="font-bold text-ink-900">{tisoc(poraba.izhodni)}</dd>
        </div>
      </dl>

      {urejam ? (
        <form onSubmit={shrani} className="flex flex-wrap items-end gap-2">
          <label className="flex w-28 flex-col gap-1 text-xs font-semibold text-ink-600">
            Mesečno ($)
            <input value={mesecni} onChange={(e) => setMesecni(e.target.value)} inputMode="decimal" title="Mesečni krediti v dolarjih" className={POLJE} />
          </label>
          <label className="flex w-28 flex-col gap-1 text-xs font-semibold text-ink-600">
            Dan obnove
            <input value={dan} onChange={(e) => setDan(e.target.value)} inputMode="numeric" title="Dan v mesecu, ko se krediti obnovijo" className={POLJE} />
          </label>
          <Button variant="neutral" hint="Zapri urejanje brez shranjevanja" onClick={() => setUrejam(false)}>
            Prekliči
          </Button>
          <Button type="submit" variant="success" hint="Shrani mesečni proračun kreditov">
            Shrani
          </Button>
        </form>
      ) : (
        <div className="flex justify-end">
          <Button variant="neutral" icon={Pencil} hint="Uredi mesečni proračun in dan obnove" onClick={() => setUrejam(true)}>
            Proračun
          </Button>
        </div>
      )}
    </section>
  );
}

function ZavrniOkno({ zahteva, onClose, onPotrdi }: { zahteva: Zahteva | null; onClose: () => void; onPotrdi: (opomba: string) => Promise<void> }) {
  const [opomba, setOpomba] = useState("");
  return (
    <Modal
      open={!!zahteva}
      title={`Zavrni zahtevo #${zahteva?.id ?? ""}`}
      onClose={onClose}
      sirina="max-w-md"
      noga={
        <div className="flex justify-end gap-2">
          <Button variant="neutral" hint="Zapri okno brez spremembe" onClick={onClose}>
            Prekliči
          </Button>
          <Button type="submit" form="wi-zavrni-zahtevo" variant="danger" icon={Ban} hint="Zavrni zahtevo z vpisanim razlogom">
            Zavrni
          </Button>
        </div>
      }
    >
      <form
        id="wi-zavrni-zahtevo"
        onSubmit={async (e) => {
          e.preventDefault();
          await onPotrdi(opomba.trim());
          setOpomba("");
        }}
        className="flex flex-col gap-3"
      >
        <p className="text-sm text-ink-600">{zahteva?.naziv}</p>
        <label className="flex flex-col gap-1 text-xs font-semibold text-ink-600">
          Razlog (vidi ga razvojnik)
          <textarea
            required
            value={opomba}
            onChange={(e) => setOpomba(e.target.value)}
            rows={3}
            title="Zakaj je zahteva zavrnjena"
            className="rounded-lg border border-ink-200 p-3 text-sm font-normal focus:border-fines-500 focus:outline-none focus:ring-2 focus:ring-fines-100"
          />
        </label>
      </form>
    </Modal>
  );
}
