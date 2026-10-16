"use client";

import { useCallback, useEffect, useState } from "react";
import { FileSpreadsheet, Layers, ListTree, Plus, Upload, X } from "lucide-react";
import {
  naloziSifrante,
  shraniPodsekcije,
  shraniSekcije,
  type PodsekcijaVnos,
  type SekcijaVnos,
  type Sifranti,
} from "@/lib/navodila";
import { preberiSifre, uvoziSifre, zadnjiUvozSifer, type UvozIdentov, type ZadnjiUvoz } from "@/lib/identi";
import { useNeshranjeno } from "@/lib/neshranjeno";
import { Button } from "@/components/ui/Button";
import { FilterIzbira, FilterVrstica } from "@/components/ui/Filtri";
import { Modal } from "@/components/ui/Modal";
import { ErrorText, Loading, SuccessText, WarningText } from "@/components/ui/Notice";
import { SaveBar } from "@/components/ui/SaveBar";
import { useToast } from "@/components/ui/Toast";
import { UvozDropzone } from "@/components/ui/UvozDropzone";
import { Zavihki } from "@/components/ui/Zavihki";

type Pogled = "sekcije" | "podsekcije" | "sifre";

const CELICA =
  "h-9 w-full rounded-md border border-ink-200 bg-white px-2 text-sm focus:border-fines-500 focus:outline-none focus:ring-2 focus:ring-fines-100";

/** Admin - Nastavitve: šifranti navodil (sekcije, podsekcije) in uvoz šifranta artiklov. */
export function Nastavitve() {
  const [pogled, setPogled] = useState<Pogled>("sekcije");
  const [sifranti, setSifranti] = useState<Sifranti | null>(null);
  const [napaka, setNapaka] = useState<string | null>(null);

  // verzija: po shranjevanju se urejevalnik na novo sestavi iz prebranih podatkov
  const [verzija, setVerzija] = useState(0);
  const uporabi = useCallback((s: Sifranti) => {
    setSifranti(s);
    setVerzija((v) => v + 1);
  }, []);
  const nalozi = async () => uporabi(await naloziSifrante(true));
  useEffect(() => {
    naloziSifrante(true).then(uporabi, (e: Error) => setNapaka(e.message));
  }, [uporabi]);

  if (napaka) return <ErrorText>{napaka}</ErrorText>;
  if (!sifranti) return <Loading />;

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-4">
      <div className="min-w-[min(100%,18rem)] flex-1">
        <h2 className="text-xl font-bold text-ink-900">Nastavitve</h2>
        <p className="text-sm text-ink-500">Sekcije in podsekcije navodil ter uvoz šifranta artiklov. Družine in šifre se tukaj ne urejajo.</p>
      </div>
      <div>
        <Zavihki
          label="Nastavitve"
          value={pogled}
          onChange={setPogled}
          zavihki={[
            { koda: "sekcije", label: "Sekcije", hint: "Uredi sekcije navodil (Montaža, Proizvodnja)", icon: Layers },
            { koda: "podsekcije", label: "Podsekcije", hint: "Uredi podsekcije navodil (Varjenje, Laser ...)", icon: ListTree },
            { koda: "sifre", label: "Uvoz šifer", hint: "Uvozi šifrant artiklov iz izvoza sifre.xls", icon: FileSpreadsheet },
          ]}
        />
        <div className="fp-card rounded-tl-none p-3 sm:p-4">
          {pogled === "sekcije" && <SekcijeUrejevalnik key={`s${verzija}`} sifranti={sifranti} onShranjeno={nalozi} />}
          {pogled === "podsekcije" && <PodsekcijeUrejevalnik key={`p${verzija}`} sifranti={sifranti} onShranjeno={nalozi} />}
          {pogled === "sifre" && <UvozSifer />}
        </div>
      </div>
    </div>
  );
}

// =====================================================================
// SEKCIJE / PODSEKCIJE - tabela-obrazec (urejanje v vrsticah)
// =====================================================================

type Vrstica = PodsekcijaVnos & { kljuc: string };

function useUrejanje(zacetne: Vrstica[]) {
  const [vrstice, setVrstice] = useState(zacetne);
  const izvorne = new Map(zacetne.map((v) => [v.kljuc, JSON.stringify(v)]));
  const spremenjene = vrstice.filter((v) => izvorne.get(v.kljuc) !== JSON.stringify(v));
  useNeshranjeno(spremenjene.length > 0);
  const nastavi = (kljuc: string, sprememba: Partial<Vrstica>) =>
    setVrstice((vs) => vs.map((v) => (v.kljuc === kljuc ? { ...v, ...sprememba } : v)));
  return { vrstice, setVrstice, spremenjene, nastavi, ponastavi: () => setVrstice(zacetne) };
}

function preveri(vrstice: Vrstica[], vse: Vrstica[]): string | null {
  for (const v of vrstice) {
    if (!v.koda.trim() || !v.naziv.trim()) return "Vsaka vrstica mora imeti kodo in naziv.";
    if (vse.some((x) => x.kljuc !== v.kljuc && x.sekcija_id === v.sekcija_id && x.koda.trim().toUpperCase() === v.koda.trim().toUpperCase()))
      return `Koda ${v.koda} je podvojena.`;
  }
  return null;
}

function SekcijeUrejevalnik({ sifranti, onShranjeno }: { sifranti: Sifranti; onShranjeno: () => Promise<void> }) {
  const notify = useToast();
  const [shranjujem, setShranjujem] = useState(false);
  const u = useUrejanje(sifranti.sekcije.map((s) => ({ ...s, sekcija_id: 0, kljuc: String(s.id) })));

  async function shrani() {
    const n = preveri(u.spremenjene, u.vrstice);
    if (n) return notify("warning", n);
    setShranjujem(true);
    try {
      await shraniSekcije(
        u.spremenjene.map(
          (v): SekcijaVnos => ({ id: v.id, koda: v.koda.trim().toUpperCase(), naziv: v.naziv.trim(), opis: v.opis?.trim() || null, vrstni_red: v.vrstni_red, visible: v.visible }),
        ),
      );
      notify("success", "Sekcije so shranjene.");
      await onShranjeno();
    } catch (e) {
      notify("error", (e as Error).message);
    } finally {
      setShranjujem(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-ink-600">Koda sekcije (npr. MO) je prvi del internega ID programa.</p>
        <Button
          hint="Dodaj novo sekcijo navodil"
          variant="success"
          icon={Plus}
          onClick={() =>
            u.setVrstice((vs) => [
              ...vs,
              { kljuc: `nova-${Date.now()}`, sekcija_id: 0, koda: "", naziv: "", opis: null, vrstni_red: vs.length + 1, visible: true },
            ])
          }
        >
          Dodaj sekcijo
        </Button>
      </div>
      <TabelaVrstic u={u} />
      <SaveBar
        vKartici
        steviloSprememb={u.spremenjene.length}
        shranjujem={shranjujem}
        onSave={shrani}
        onReset={u.ponastavi}
        shraniLabel="Shrani sekcije"
        shraniHint="Shrani spremembe sekcij v bazo"
      />
    </div>
  );
}

function PodsekcijeUrejevalnik({ sifranti, onShranjeno }: { sifranti: Sifranti; onShranjeno: () => Promise<void> }) {
  const notify = useToast();
  const [shranjujem, setShranjujem] = useState(false);
  const [sekcija, setSekcija] = useState<number>(0);
  const u = useUrejanje(sifranti.podsekcije.map((p) => ({ ...p, kljuc: String(p.id) })));

  async function shrani() {
    const n = preveri(u.spremenjene, u.vrstice);
    if (n) return notify("warning", n);
    if (u.spremenjene.some((v) => !v.sekcija_id)) return notify("warning", "Vsaka podsekcija mora imeti sekcijo.");
    setShranjujem(true);
    try {
      await shraniPodsekcije(
        u.spremenjene.map(
          (v): PodsekcijaVnos => ({
            id: v.id,
            sekcija_id: v.sekcija_id,
            koda: v.koda.trim().toUpperCase(),
            naziv: v.naziv.trim(),
            opis: v.opis?.trim() || null,
            vrstni_red: v.vrstni_red,
            visible: v.visible,
          }),
        ),
      );
      notify("success", "Podsekcije so shranjene.");
      await onShranjeno();
    } catch (e) {
      notify("error", (e as Error).message);
    } finally {
      setShranjujem(false);
    }
  }

  const sekcijeOpcije = sifranti.sekcije.map((s) => ({ value: s.id, label: `${s.koda} - ${s.naziv}` }));

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <FilterVrstica>
          <FilterIzbira
            label="Sekcija"
            value={sekcija}
            options={[{ value: 0, label: "Vse sekcije" }, ...sekcijeOpcije]}
            onChange={setSekcija}
            hint="Prikaži podsekcije izbrane sekcije"
          />
        </FilterVrstica>
        <Button
          hint="Dodaj novo podsekcijo navodil"
          variant="success"
          icon={Plus}
          disabled={!sifranti.sekcije.length}
          onClick={() =>
            u.setVrstice((vs) => [
              ...vs,
              {
                kljuc: `nova-${Date.now()}`,
                sekcija_id: sekcija || sifranti.sekcije[0].id,
                koda: "",
                naziv: "",
                opis: null,
                vrstni_red: vs.filter((v) => v.sekcija_id === (sekcija || sifranti.sekcije[0].id)).length + 1,
                visible: true,
              },
            ])
          }
        >
          Dodaj podsekcijo
        </Button>
      </div>
      <p className="text-sm text-ink-600">Koda podsekcije (npr. VAR) je drugi del internega ID programa. Sprememba kode velja za nove programe.</p>
      <TabelaVrstic u={u} sekcije={sekcijeOpcije} filter={sekcija} />
      <SaveBar
        vKartici
        steviloSprememb={u.spremenjene.length}
        shranjujem={shranjujem}
        onSave={shrani}
        onReset={u.ponastavi}
        shraniLabel="Shrani podsekcije"
        shraniHint="Shrani spremembe podsekcij v bazo"
      />
    </div>
  );
}

/** Tabela-obrazec (vrstice z vnosnimi polji, zato brez razvrščanja). */
function TabelaVrstic({
  u,
  sekcije,
  filter = 0,
}: {
  u: ReturnType<typeof useUrejanje>;
  sekcije?: { value: number; label: string }[];
  filter?: number;
}) {
  const prikazane = u.vrstice
    .filter((v) => !filter || v.sekcija_id === filter)
    .sort((a, b) => (sekcije ? a.sekcija_id - b.sekcija_id : 0) || a.vrstni_red - b.vrstni_red);
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[40rem] text-sm">
        <thead className="fp-thead">
          <tr>
            {sekcije && <th className="px-2 py-2">Sekcija</th>}
            <th className="w-28 px-2 py-2">Koda</th>
            <th className="px-2 py-2">Naziv</th>
            <th className="px-2 py-2">Opis</th>
            <th className="w-24 px-2 py-2">Vrstni red</th>
            <th className="w-20 px-2 py-2 text-center">Vidna</th>
          </tr>
        </thead>
        <tbody>
          {prikazane.map((v) => (
            <tr key={v.kljuc} className={`border-b border-ink-100 ${v.visible ? "" : "bg-ink-50 text-ink-400"}`}>
              {sekcije && (
                <td className="px-2 py-1.5">
                  <select
                    value={v.sekcija_id}
                    title="Sekcija, v katero spada podsekcija"
                    onChange={(e) => u.nastavi(v.kljuc, { sekcija_id: Number(e.target.value) })}
                    className={CELICA}
                  >
                    {sekcije.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </td>
              )}
              <td className="px-2 py-1.5">
                <input
                  value={v.koda}
                  maxLength={5}
                  onChange={(e) => u.nastavi(v.kljuc, { koda: e.target.value.toUpperCase() })}
                  title="Kratka koda za interni ID (2-5 črk)"
                  className={`${CELICA} font-mono uppercase`}
                />
              </td>
              <td className="px-2 py-1.5">
                <input value={v.naziv} onChange={(e) => u.nastavi(v.kljuc, { naziv: e.target.value })} title="Naziv" className={CELICA} />
              </td>
              <td className="px-2 py-1.5">
                <input
                  value={v.opis ?? ""}
                  onChange={(e) => u.nastavi(v.kljuc, { opis: e.target.value })}
                  title="Neobvezen opis"
                  className={CELICA}
                />
              </td>
              <td className="px-2 py-1.5">
                <input
                  type="number"
                  value={v.vrstni_red}
                  onChange={(e) => u.nastavi(v.kljuc, { vrstni_red: Number(e.target.value) || 0 })}
                  title="Vrstni red prikaza"
                  className={`${CELICA} text-right tabular-nums`}
                />
              </td>
              <td className="px-2 py-1.5 text-center">
                <input
                  type="checkbox"
                  checked={v.visible}
                  onChange={(e) => u.nastavi(v.kljuc, { visible: e.target.checked })}
                  title={v.visible ? "Skrij (ne bo več na izbiro)" : "Ponovno prikaži"}
                  className="h-4 w-4 accent-fines-500"
                />
              </td>
            </tr>
          ))}
          {prikazane.length === 0 && (
            <tr>
              <td colSpan={6} className="px-2 py-8 text-center text-sm text-ink-400">
                Ni vrstic za izbrane filtre.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// =====================================================================
// UVOZ ŠIFER (spl_identi)
// =====================================================================

function UvozSifer() {
  const notify = useToast();
  const [stanje, setStanje] = useState<{ uvoz: ZadnjiUvoz | null; stevilo: number } | null>(null);
  const [berem, setBerem] = useState(false);
  const [predogled, setPredogled] = useState<UvozIdentov | null>(null);
  const [uvazam, setUvazam] = useState<number | null>(null);
  const [napaka, setNapaka] = useState<string | null>(null);

  const osvezi = useCallback(() => zadnjiUvozSifer().then(setStanje, (e: Error) => setNapaka(e.message)), []);
  useEffect(() => {
    osvezi();
  }, [osvezi]);

  async function izberi(f: File) {
    setBerem(true);
    setNapaka(null);
    try {
      setPredogled(await preberiSifre(f));
    } catch (e) {
      setNapaka((e as Error).message);
    } finally {
      setBerem(false);
    }
  }

  async function uvozi() {
    if (!predogled) return;
    setUvazam(0);
    try {
      await uvoziSifre(predogled, setUvazam);
      notify("success", `Uvoženih ${predogled.vrstice.length} šifer.`);
      setPredogled(null);
      await osvezi();
    } catch (e) {
      notify("error", (e as Error).message);
    } finally {
      setUvazam(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-[min(100%,18rem)] flex-1 text-sm text-ink-600">
          <h3 className="text-base font-bold text-ink-900">Šifrant artiklov (spl_identi)</h3>
          <p className="mt-1">
            Izvoz šifer iz ERP (sifre.xls). Uvoz posodobi obstoječe šifre in doda nove - nobena šifra se ne izbriše. V aplikaciji se
            šifre ne urejajo.
          </p>
          {stanje && (
            <p className="mt-2">
              V bazi: <strong className="tabular-nums text-ink-900">{stanje.stevilo.toLocaleString("sl-SI")}</strong> šifer
            </p>
          )}
        </div>
        <div className="w-full sm:w-72">
          <UvozDropzone
            naslov="Šifrant (sifre.xls)"
            hint="Uvozi izvoz šifranta artiklov"
            enota="šifer"
            uvoz={stanje?.uvoz ? { datoteka: stanje.uvoz.datoteka, stevilo: stanje.uvoz.stevilo, created_at: stanje.uvoz.created_at } : null}
            nalagam={berem || uvazam !== null}
            accept=".xls,.xlsx,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onFile={izberi}
          />
        </div>
      </div>
      {napaka && <ErrorText>{napaka}</ErrorText>}

      <Modal open={!!predogled} title="Uvoz šifranta" onClose={() => uvazam === null && setPredogled(null)}>
        {predogled && (
          <div className="flex flex-col gap-3 text-sm">
            <SuccessText>
              Datoteka <strong>{predogled.datoteka}</strong>: {predogled.vrstice.length.toLocaleString("sl-SI")} šifer.
            </SuccessText>
            {predogled.podvojene > 0 && <WarningText>{predogled.podvojene} podvojenih šifer - uvožena je zadnja vrstica.</WarningText>}
            {predogled.manjkajoci.length > 0 && <WarningText>Manjkajoči stolpci (ostanejo prazni): {predogled.manjkajoci.join(", ")}</WarningText>}
            {predogled.vrstice.length >= 65000 && (
              <WarningText>Datoteka ima skoraj 65.536 vrstic (meja formata .xls) - izvoz je morda nepopoln.</WarningText>
            )}
            {uvazam !== null && (
              <p className="font-semibold text-sync-600">
                Nalagam ... {uvazam.toLocaleString("sl-SI")} / {predogled.vrstice.length.toLocaleString("sl-SI")}
              </p>
            )}
            <div className="flex justify-end gap-2 border-t border-ink-100 pt-3">
              <Button hint="Zapri brez uvoza" variant="neutral" icon={X} disabled={uvazam !== null} onClick={() => setPredogled(null)}>
                Prekliči
              </Button>
              <Button hint="Naloži šifre v bazo" variant="success" icon={Upload} disabled={uvazam !== null} onClick={uvozi}>
                Uvozi
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
