"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowUp, GripVertical, ImagePlus, Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import {
  MAX_SLIK,
  dodajKorak,
  dodajPripravo,
  naloziPripravo,
  odstraniPripravo,
  prerazporediPripravo,
  shraniPripravo,
  type Priprava,
  dodajSliko,
  izbrisiSliko,
  naloziKorake,
  odstraniKorak,
  podsekcijaLabel,
  prenesiSliko,
  prerazporediKorake,
  prerazporediSlike,
  shraniKorak,
  shraniOpisSlike,
  zamenjajSliko,
  type Korak,
  type Program,
  type Sifranti,
  type Slika,
} from "@/lib/navodila";
import { useNeshranjeno } from "@/lib/neshranjeno";
import { druzineProgramaText } from "./ProgramSeznam";
import { PripravaBlok } from "./PripravaBlok";
import { KoncnaSlikaBlok } from "./KoncnaSlikaBlok";
import { Button, IconButton } from "@/components/ui/Button";
import { ErrorText, Loading } from "@/components/ui/Notice";
import { SaveBar } from "@/components/ui/SaveBar";
import { Tabla } from "@/components/ui/Tabla";
import { useToast } from "@/components/ui/Toast";

const POLJE =
  "w-full rounded-lg border border-ink-200 bg-white px-3 text-sm focus:border-fines-500 focus:outline-none focus:ring-2 focus:ring-fines-100";

type KorakSpr = { naziv: string; opis: string };

/**
 * Oblikovalec korakov programa: koraki so bloki eden pod drugim (ime, opis, do 6 slik z opisom).
 * Besedila se shranijo z gumbom Shrani (spodnja vrstica), slike in vrstni red takoj.
 */
export function KorakiUrejevalnik({
  program,
  sifranti,
  onStKorakov,
  onProgram,
}: {
  program: Program;
  sifranti: Sifranti;
  onStKorakov: (n: number) => void;
  /** Program se je spremenil (npr. končna slika). */
  onProgram: (p: Program) => void;
}) {
  const notify = useToast();
  const [koraki, setKoraki] = useState<Korak[] | null>(null);
  const [napaka, setNapaka] = useState<string | null>(null);
  const [korakSpr, setKorakSpr] = useState<Record<number, KorakSpr>>({});
  const [slikaSpr, setSlikaSpr] = useState<Record<number, string>>({});
  const [shranjujem, setShranjujem] = useState(false);
  const [delam, setDelam] = useState(false);
  const [tabla, setTabla] = useState<{ slika: Slika; blob: Blob } | null>(null);
  const [novKorak, setNovKorak] = useState<number | null>(null);
  const [priprava, setPriprava] = useState<Priprava[]>([]);
  const [pripravaSpr, setPripravaSpr] = useState<Record<number, string>>({});

  const steviloSprememb = Object.keys(korakSpr).length + Object.keys(slikaSpr).length + Object.keys(pripravaSpr).length;
  useNeshranjeno(steviloSprememb > 0);

  useEffect(() => {
    Promise.all([naloziKorake(program.id), naloziPripravo(program.id)])
      .then(([k, p]) => {
        setPriprava(p);
        setKoraki(k);
      })
      .catch((e: Error) => setNapaka(e.message));
  }, [program.id]);

  if (napaka) return <ErrorText>{napaka}</ErrorText>;
  if (!koraki) return <Loading />;

  function nastaviKoraka(k: Korak, polje: keyof KorakSpr, v: string) {
    setKorakSpr((s) => {
      const nov = { ...(s[k.id] ?? { naziv: k.naziv, opis: k.opis ?? "" }), [polje]: v };
      const kopija = { ...s };
      if (nov.naziv === k.naziv && nov.opis === (k.opis ?? "")) delete kopija[k.id];
      else kopija[k.id] = nov;
      return kopija;
    });
  }

  function nastaviOpisSlike(s: Slika, v: string) {
    setSlikaSpr((st) => {
      const kopija = { ...st };
      if (v === (s.opis ?? "")) delete kopija[s.id];
      else kopija[s.id] = v;
      return kopija;
    });
  }

  async function shrani() {
    setShranjujem(true);
    try {
      for (const [id, v] of Object.entries(korakSpr)) await shraniKorak(Number(id), v.naziv, v.opis);
      for (const [id, v] of Object.entries(slikaSpr)) await shraniOpisSlike(Number(id), v);
      for (const [id, v] of Object.entries(pripravaSpr)) if (v.trim()) await shraniPripravo(Number(id), v);
      setPriprava((ps) => ps.map((p) => (pripravaSpr[p.id]?.trim() ? { ...p, naziv: pripravaSpr[p.id].trim() } : p)));
      setPripravaSpr({});
      setKoraki((ks) =>
        ks!.map((k) => ({
          ...k,
          ...(korakSpr[k.id] ? { naziv: korakSpr[k.id].naziv.trim(), opis: korakSpr[k.id].opis.trim() || null } : {}),
          slike: k.slike.map((s) => (slikaSpr[s.id] !== undefined ? { ...s, opis: slikaSpr[s.id].trim() || null } : s)),
        })),
      );
      setKorakSpr({});
      setSlikaSpr({});
      notify("success", "Spremembe so shranjene.");
    } catch (e) {
      notify("error", (e as Error).message);
    } finally {
      setShranjujem(false);
    }
  }

  /** Izvede akcijo nad bazo (slike, vrstni red ...) in javi napako. */
  async function izvedi(akcija: () => Promise<void>) {
    setDelam(true);
    try {
      await akcija();
    } catch (e) {
      notify("error", (e as Error).message);
    } finally {
      setDelam(false);
    }
  }

  const posodobiKorak = (id: number, f: (k: Korak) => Korak) => setKoraki((ks) => ks!.map((k) => (k.id === id ? f(k) : k)));

  const dodaj = () =>
    izvedi(async () => {
      const k = await dodajKorak(program.id, Math.max(0, ...koraki.map((x) => x.vrstni_red)) + 1);
      setKoraki([...koraki, k]);
      setNovKorak(k.id);
      onStKorakov(koraki.length + 1);
    });

  const odstrani = (k: Korak, i: number) => {
    if (!window.confirm(`Odstranim korak ${i + 1}${k.naziv ? ` - ${k.naziv}` : ""} in njegove slike?`)) return;
    izvedi(async () => {
      await odstraniKorak(k);
      setKoraki(koraki.filter((x) => x.id !== k.id));
      setKorakSpr((st) => Object.fromEntries(Object.entries(st).filter(([id]) => Number(id) !== k.id)));
      setSlikaSpr((st) => Object.fromEntries(Object.entries(st).filter(([id]) => !k.slike.some((s) => s.id === Number(id)))));
      onStKorakov(koraki.length - 1);
    });
  };

  const premakni = (i: number, smer: -1 | 1) =>
    izvedi(async () => {
      const nov = [...koraki];
      [nov[i], nov[i + smer]] = [nov[i + smer], nov[i]];
      await prerazporediKorake(nov.map((k) => k.id));
      setKoraki(nov.map((k, j) => ({ ...k, vrstni_red: j + 1 })));
    });

  const naloziSlike = (k: Korak, datoteke: File[]) =>
    izvedi(async () => {
      const prostih = MAX_SLIK - k.slike.length;
      const slike = datoteke.filter((f) => f.type.startsWith("image/"));
      if (slike.length > prostih) notify("warning", `Korak ima lahko največ ${MAX_SLIK} slik - dodanih ${Math.max(0, prostih)}.`);
      let korak = k;
      for (const f of slike.slice(0, Math.max(0, prostih))) {
        const s = await dodajSliko(korak, f);
        korak = { ...korak, slike: [...korak.slike, s] };
        posodobiKorak(k.id, (x) => ({ ...x, slike: [...x.slike, s] }));
      }
    });

  /** Nov vrstni red slik (povleci in spusti): takoj na zaslonu, nato v bazo. */
  const razvrstiSlike = (k: Korak, idji: number[]) => {
    const prej = k.slike;
    const nove = idji.map((id, i) => ({ ...prej.find((s) => s.id === id)!, vrstni_red: i + 1 }));
    posodobiKorak(k.id, (x) => ({ ...x, slike: nove }));
    izvedi(async () => {
      try {
        await prerazporediSlike(idji);
      } catch (e) {
        posodobiKorak(k.id, (x) => ({ ...x, slike: prej }));
        throw e;
      }
    });
  };

  const izbrisi = (k: Korak, s: Slika) => {
    if (!window.confirm("Izbrišem sliko?")) return;
    izvedi(async () => {
      await izbrisiSliko(s);
      posodobiKorak(k.id, (x) => ({ ...x, slike: x.slike.filter((y) => y.id !== s.id) }));
      setSlikaSpr((st) => Object.fromEntries(Object.entries(st).filter(([id]) => Number(id) !== s.id)));
    });
  };

  const uredi = (s: Slika) =>
    izvedi(async () => {
      setTabla({ slika: s, blob: await prenesiSliko(s) });
    });

  async function shraniUrejeno(png: Blob) {
    if (!tabla) return;
    try {
      const nova = await zamenjajSliko(tabla.slika, program.id, png);
      posodobiKorak(nova.korak_id, (x) => ({ ...x, slike: x.slike.map((y) => (y.id === nova.id ? { ...nova, opis: y.opis } : y)) }));
      setTabla(null);
      notify("success", "Urejena slika je shranjena.");
    } catch (e) {
      notify("error", (e as Error).message);
    }
  }

  const podsekcije = program.podsekcije
    .map((id) => sifranti.podsekcije.find((p) => p.id === id))
    .filter((p) => p !== undefined)
    .map((p) => podsekcijaLabel(p, sifranti.sekcije));

  return (
    <section className="flex min-w-0 flex-col gap-4">
      {/* glava programa */}
      <div className="fp-card flex flex-wrap items-start gap-3 border-l-4 border-l-fines-500 p-3 sm:p-4">
        <div className="min-w-[min(100%,18rem)] flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-ink-800 px-2 py-0.5 font-mono text-xs font-bold text-white">{program.interni_id}</span>
            <span className="text-xs text-ink-400">ID {program.id}</span>
            {podsekcije.map((p) => (
              <span key={p} className="rounded-full bg-fines-50 px-2 py-0.5 text-xs font-semibold text-fines-700">
                {p}
              </span>
            ))}
          </div>
          <h2 className="mt-1 text-xl font-bold text-ink-900">{program.naziv}</h2>
          {program.opis && <p className="whitespace-pre-wrap text-sm text-ink-600">{program.opis}</p>}
          <p className="mt-1 text-xs text-ink-500">Družine: {druzineProgramaText(program, sifranti) || "-"}</p>
        </div>
        <Button hint="Dodaj nov korak na konec navodila" variant="success" icon={Plus} disabled={delam} onClick={dodaj}>
          Dodaj korak
        </Button>
      </div>

      {/* priprava (80 %) in končna slika proizvoda (20 %) */}
      <div className="grid items-start gap-4 sm:grid-cols-[minmax(0,4fr)_minmax(9rem,1fr)]">
        <PripravaBlok
          postavke={priprava}
          spremembe={pripravaSpr}
          delam={delam}
          onSpremeni={(p, v) =>
            setPripravaSpr((st) => {
              const kopija = { ...st };
              if (v === p.naziv) delete kopija[p.id];
              else kopija[p.id] = v;
              return kopija;
            })
          }
          onDodaj={(nazivi) =>
            izvedi(async () => {
              const nove = await dodajPripravo(program.id, nazivi, Math.max(0, ...priprava.map((p) => p.vrstni_red)) + 1);
              setPriprava((ps) => [...ps, ...nove]);
            })
          }
          onOdstrani={(p) =>
            izvedi(async () => {
              await odstraniPripravo(p.id);
              setPriprava((ps) => ps.filter((x) => x.id !== p.id));
              setPripravaSpr((st) => Object.fromEntries(Object.entries(st).filter(([id]) => Number(id) !== p.id)));
            })
          }
          onRazvrsti={(idji) => {
            const prej = priprava;
            setPriprava(idji.map((id, i) => ({ ...prej.find((p) => p.id === id)!, vrstni_red: i + 1 })));
            izvedi(async () => {
              try {
                await prerazporediPripravo(idji);
              } catch (e) {
                setPriprava(prej);
                throw e;
              }
            });
          }}
        />

        <KoncnaSlikaBlok program={program} onSprememba={onProgram} />
      </div>

      <div className="flex items-center gap-2 pt-1">
        <span className="shrink-0 text-xs font-bold uppercase tracking-wider text-fines-500">Koraki navodila ({koraki.length})</span>
        <span className="h-px flex-1 bg-fines-200" aria-hidden />
      </div>

      {koraki.length === 0 && (
        <div className="fp-card p-8 text-center text-sm text-ink-500">Program še nima korakov. Klikni &quot;Dodaj korak&quot;.</div>
      )}

      {koraki.map((k, i) => (
        <KorakBlok
          key={k.id}
          korak={k}
          stevilka={i + 1}
          prvi={i === 0}
          zadnji={i === koraki.length - 1}
          sprememba={korakSpr[k.id]}
          opisiSlik={slikaSpr}
          delam={delam}
          fokus={novKorak === k.id}
          onNaziv={(v) => nastaviKoraka(k, "naziv", v)}
          onOpis={(v) => nastaviKoraka(k, "opis", v)}
          onOpisSlike={nastaviOpisSlike}
          onGor={() => premakni(i, -1)}
          onDol={() => premakni(i, 1)}
          onOdstrani={() => odstrani(k, i)}
          onSlike={(f) => naloziSlike(k, f)}
          onUredi={uredi}
          onIzbrisi={(s) => izbrisi(k, s)}
          onRazvrstiSlike={(idji) => razvrstiSlike(k, idji)}
        />
      ))}

      {koraki.length > 0 && (
        <button
          type="button"
          title="Dodaj nov korak na konec navodila"
          disabled={delam}
          onClick={dodaj}
          className="flex h-14 items-center justify-center gap-2 rounded-xl border-2 border-dashed border-ink-300 text-sm font-semibold text-ink-500 transition-colors hover:border-ok-500 hover:bg-ok-50 hover:text-ok-600 disabled:opacity-50"
        >
          <Plus className="h-5 w-5" aria-hidden />
          Dodaj korak
        </button>
      )}

      <SaveBar
        steviloSprememb={steviloSprememb}
        shranjujem={shranjujem}
        onSave={shrani}
        onReset={() => {
          setKorakSpr({});
          setSlikaSpr({});
          setPripravaSpr({});
        }}
        vKartici
        shraniLabel="Shrani"
        shraniHint="Shrani pripravo, besedila korakov in opise slik"
      />

      {tabla && (
        <Tabla
          naslov={`Urejanje slike${tabla.slika.opis ? ` - ${tabla.slika.opis}` : ""}`}
          ozadje={tabla.blob}
          onClose={() => setTabla(null)}
          onShrani={shraniUrejeno}
        />
      )}
    </section>
  );
}

function KorakBlok({
  korak,
  stevilka,
  prvi,
  zadnji,
  sprememba,
  opisiSlik,
  delam,
  fokus,
  onNaziv,
  onOpis,
  onOpisSlike,
  onGor,
  onDol,
  onOdstrani,
  onSlike,
  onUredi,
  onIzbrisi,
  onRazvrstiSlike,
}: {
  korak: Korak;
  stevilka: number;
  prvi: boolean;
  zadnji: boolean;
  sprememba?: KorakSpr;
  opisiSlik: Record<number, string>;
  delam: boolean;
  fokus: boolean;
  onNaziv: (v: string) => void;
  onOpis: (v: string) => void;
  onOpisSlike: (s: Slika, v: string) => void;
  onGor: () => void;
  onDol: () => void;
  onOdstrani: () => void;
  onSlike: (f: File[]) => void;
  onUredi: (s: Slika) => void;
  onIzbrisi: (s: Slika) => void;
  onRazvrstiSlike: (idji: number[]) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const nazivRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [nadOknom, setNadOknom] = useState(false);
  // vlečenje slike za spremembo vrstnega reda
  const [vlecem, setVlecem] = useState<number | null>(null);
  const [nadSliko, setNadSliko] = useState<number | null>(null);

  function spusti(cilj: number) {
    if (vlecem === null || vlecem === cilj) return;
    const idji = korak.slike.map((s) => s.id).filter((id) => id !== vlecem);
    const iCilj = korak.slike.findIndex((s) => s.id === cilj);
    const iVir = korak.slike.findIndex((s) => s.id === vlecem);
    // spuščeno na sliko: vlečena slika zasede njeno mesto
    idji.splice(iVir < iCilj ? iCilj : idji.indexOf(cilj), 0, vlecem);
    onRazvrstiSlike(idji);
  }
  const naziv = sprememba?.naziv ?? korak.naziv;
  const opis = sprememba?.opis ?? korak.opis ?? "";
  const lahkoDodam = korak.slike.length < MAX_SLIK;

  // nov korak: pomakni na zaslon in postavi kurzor v ime
  useEffect(() => {
    if (!fokus) return;
    ref.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    nazivRef.current?.focus({ preventScroll: true });
  }, [fokus]);

  return (
    <div
      ref={ref}
      className={`fp-card flex flex-col gap-3 p-3 sm:p-4 ${sprememba ? "border-warn-400" : ""}`}
      onDragOver={(e) => {
        if (!lahkoDodam || !e.dataTransfer.types.includes("Files")) return;
        e.preventDefault();
        setNadOknom(true);
      }}
      onDragLeave={() => setNadOknom(false)}
      onDrop={(e) => {
        if (!e.dataTransfer.files.length) return;
        e.preventDefault();
        setNadOknom(false);
        onSlike([...e.dataTransfer.files]);
      }}
    >
      <div className="flex items-center gap-2">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-fines-500 font-bold text-white">{stevilka}</span>
        <span className="flex-1 text-xs text-ink-400">
          Korak {stevilka} · ID {korak.id}
        </span>
        <IconButton hint="Premakni korak višje" variant="neutral" icon={ArrowUp} disabled={prvi || delam} onClick={onGor} />
        <IconButton hint="Premakni korak nižje" variant="neutral" icon={ArrowDown} disabled={zadnji || delam} onClick={onDol} />
        <IconButton hint="Odstrani korak in njegove slike" variant="danger" icon={Trash2} disabled={delam} onClick={onOdstrani} />
      </div>

      <label className="flex flex-col gap-1 text-xs font-semibold text-ink-600">
        Ime koraka
        <input
          ref={nazivRef}
          value={naziv}
          maxLength={150}
          onChange={(e) => onNaziv(e.target.value)}
          placeholder="npr. Priprava sestavnih delov"
          title="Kratko ime koraka"
          className={`${POLJE} h-10 text-base font-semibold`}
        />
      </label>
      <label className="flex flex-col gap-1 text-xs font-semibold text-ink-600">
        Opis koraka
        <textarea
          value={opis}
          rows={3}
          onChange={(e) => onOpis(e.target.value)}
          placeholder="Kaj in kako naj delavec naredi ..."
          title="Podroben opis dela v koraku"
          className={`${POLJE} py-2 font-normal`}
        />
      </label>

      <div>
        <div className="mb-1 text-xs font-semibold text-ink-600">
          Slike ({korak.slike.length}/{MAX_SLIK})
          {korak.slike.length > 1 && <span className="ml-2 font-normal text-ink-400">vrstni red spremeniš tako, da sliko povlečeš na drugo mesto</span>}
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          {korak.slike.map((s, i) => (
            <div
              key={s.id}
              draggable={!delam && korak.slike.length > 1}
              onDragStart={(e) => {
                e.dataTransfer.setData("application/x-wi-slika", String(s.id));
                e.dataTransfer.effectAllowed = "move";
                setVlecem(s.id);
              }}
              onDragEnd={() => {
                setVlecem(null);
                setNadSliko(null);
              }}
              onDragOver={(e) => {
                if (vlecem === null) return;
                e.preventDefault();
                e.stopPropagation();
                e.dataTransfer.dropEffect = "move";
                if (nadSliko !== s.id) setNadSliko(s.id);
              }}
              onDragLeave={() => setNadSliko((n) => (n === s.id ? null : n))}
              onDrop={(e) => {
                if (vlecem === null) return;
                e.preventDefault();
                e.stopPropagation();
                spusti(s.id);
                setVlecem(null);
                setNadSliko(null);
              }}
              className={`flex flex-col gap-1.5 rounded-lg border p-1.5 transition-all ${
                vlecem === s.id
                  ? "border-fines-500 bg-fines-50 opacity-40"
                  : nadSliko === s.id
                    ? "border-2 border-dashed border-fines-500 bg-fines-50"
                    : "border-ink-200 bg-ink-50"
              }`}
            >
              <div className="relative overflow-hidden rounded-md bg-ink-100">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={s.url} alt={s.opis ?? "Slika koraka"} draggable={false} className="aspect-[4/3] w-full object-contain" />
                <div
                  className={`absolute left-1 top-1 flex h-8 items-center gap-0.5 rounded-full bg-ink-900/80 pl-1 pr-2.5 text-sm font-bold text-white ${
                    korak.slike.length > 1 ? "cursor-grab active:cursor-grabbing" : ""
                  }`}
                  title={korak.slike.length > 1 ? "Povleci sliko na drugo mesto (vrstni red)" : `Slika ${i + 1}`}
                >
                  {korak.slike.length > 1 ? <GripVertical className="h-4 w-4 opacity-70" aria-hidden /> : <span className="w-1.5" />}
                  {i + 1}
                </div>
                <div className="absolute right-1 top-1 flex gap-1">
                  <IconButton hint="Uredi sliko v slikarju (risanje)" variant="primary" icon={Pencil} disabled={delam} onClick={() => onUredi(s)} />
                  <IconButton hint="Izbriši sliko iz koraka" variant="danger" icon={Trash2} disabled={delam} onClick={() => onIzbrisi(s)} />
                </div>
              </div>
              <input
                value={opisiSlik[s.id] ?? s.opis ?? ""}
                onChange={(e) => onOpisSlike(s, e.target.value)}
                placeholder="Opis slike ..."
                title="Kratek opis, kaj slika prikazuje"
                className={`${POLJE} h-9 ${opisiSlik[s.id] !== undefined ? "border-warn-400" : ""}`}
              />
            </div>
          ))}
          {lahkoDodam && (
            <button
              type="button"
              title="Dodaj sliko - klikni ali povleci datoteko"
              disabled={delam}
              onClick={() => fileRef.current?.click()}
              className={`flex aspect-[4/3] flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed text-sm font-semibold transition-colors disabled:cursor-wait ${
                nadOknom ? "border-fines-500 bg-fines-50 text-fines-600" : "border-ink-300 bg-ink-50 text-ink-500 hover:border-ink-400 hover:bg-ink-100"
              }`}
            >
              {delam ? <Loader2 className="h-7 w-7 animate-spin text-sync-500" aria-hidden /> : <ImagePlus className="h-7 w-7" aria-hidden />}
              Dodaj sliko
              <span className="text-xs font-normal">klikni ali povleci sem</span>
            </button>
          )}
        </div>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(e) => {
            onSlike([...(e.target.files ?? [])]);
            e.target.value = "";
          }}
        />
      </div>
    </div>
  );
}
