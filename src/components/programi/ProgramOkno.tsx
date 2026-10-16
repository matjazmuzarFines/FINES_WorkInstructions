"use client";

import { useState } from "react";
import { ArrowLeft, Copy, Plus, Save, X } from "lucide-react";
import { podsekcijaLabel, predponaId, type Program, type ProgramVnos, type Sifranti } from "@/lib/navodila";
import { Button } from "@/components/ui/Button";
import { FilterIskanje } from "@/components/ui/Filtri";
import { Modal } from "@/components/ui/Modal";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { ErrorText } from "@/components/ui/Notice";
import { ujemaIskanje } from "@/lib/iskanje";

const POLJE =
  "w-full rounded-lg border border-ink-200 bg-white px-3 text-sm focus:border-fines-500 focus:outline-none focus:ring-2 focus:ring-fines-100";

/**
 * Okno za dodajanje / urejanje programa: ime, opis, družine, podsekcije.
 * Pri dodajanju "Kopiraj iz obstoječega" izbere program, katerega priprava in koraki (s slikami) se kopirajo.
 */
export function ProgramOkno({
  program,
  programi,
  sifranti,
  onClose,
  onShrani,
}: {
  /** null = nov program */
  program: Program | null;
  programi: Program[];
  sifranti: Sifranti;
  onClose: () => void;
  onShrani: (vnos: ProgramVnos, kopirajIz?: number) => Promise<void>;
}) {
  const [naziv, setNaziv] = useState(program?.naziv ?? "");
  const [opis, setOpis] = useState(program?.opis ?? "");
  const [druzine, setDruzine] = useState<number[]>(program?.druzine ?? []);
  const [podsekcije, setPodsekcije] = useState<number[]>(program?.podsekcije ?? []);
  const [kopija, setKopija] = useState<Program | null>(null);
  const [izbiram, setIzbiram] = useState(false);
  const [iskanje, setIskanje] = useState("");
  const [napaka, setNapaka] = useState<string | null>(null);
  const [shranjujem, setShranjujem] = useState(false);

  const podLabel = (id: number) => {
    const p = sifranti.podsekcije.find((x) => x.id === id);
    return p ? podsekcijaLabel(p, sifranti.sekcije) : "";
  };
  const podOpcije = sifranti.podsekcije.map((p) => ({ id: p.id, label: podsekcijaLabel(p, sifranti.sekcije) }));
  const druzinaOpcije = sifranti.druzine.map((d) => ({ id: d.id, label: d.koda }));

  function izberiKopijo(p: Program) {
    setKopija(p);
    setIzbiram(false);
    // ime in opis se zamenjata - predlog iz izvornega programa, če še nista vpisana
    if (!naziv.trim()) setNaziv(`${p.naziv} (kopija)`);
    if (!opis.trim()) setOpis(p.opis ?? "");
    setDruzine(p.druzine);
    setPodsekcije(p.podsekcije);
  }

  async function shrani() {
    if (!naziv.trim()) return setNapaka("Vpiši ime programa.");
    if (!podsekcije.length) return setNapaka("Izberi vsaj eno podsekcijo (določa interni ID).");
    setNapaka(null);
    setShranjujem(true);
    try {
      await onShrani({ naziv, opis, druzine, podsekcije }, kopija?.id);
    } catch (e) {
      setNapaka((e as Error).message);
      setShranjujem(false);
    }
  }


  const zaKopijo = programi.filter(
    (p) => ujemaIskanje([p.interni_id, p.naziv, p.opis ?? ""].join(" "), iskanje),
  );
  const internId = program?.interni_id ?? `${predponaId(podsekcije[0], sifranti)}-xxx`;

  return (
    <Modal open title={program ? "Uredi program" : izbiram ? "Kopiraj iz obstoječega programa" : "Nov program"} onClose={onClose} sirina="max-w-2xl">
      {izbiram ? (
        <div className="flex flex-col gap-3">
          <FilterIskanje
            value={iskanje}
            onChange={setIskanje}
            placeholder="ID, ime ali opis ..."
            hint="Išči program, ki ga želiš kopirati"
            className="w-full"
          />
          <div className="flex max-h-[50vh] flex-col gap-1 overflow-y-auto">
            {zaKopijo.map((p) => (
              <button
                key={p.id}
                type="button"
                title={`Kopiraj korake programa ${p.interni_id}`}
                onClick={() => izberiKopijo(p)}
                className="flex items-start gap-3 rounded-lg border border-ink-200 px-3 py-2 text-left hover:border-fines-500 hover:bg-fines-50"
              >
                <span className="mt-0.5 font-mono text-xs font-semibold text-ink-700">{p.interni_id}</span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-semibold text-ink-900">{p.naziv}</span>
                  {p.opis && <span className="line-clamp-1 text-xs text-ink-500">{p.opis}</span>}
                </span>
                <span className="text-xs tabular-nums text-ink-500">{p.stKorakov} korakov</span>
              </button>
            ))}
            {zaKopijo.length === 0 && <p className="py-6 text-center text-sm text-ink-400">Ni programov.</p>}
          </div>
          <div className="flex justify-end">
            <Button hint="Vrni se na vnos programa" variant="neutral" icon={ArrowLeft} onClick={() => setIzbiram(false)}>
              Nazaj
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2 text-sm text-ink-600" title="Interni ID: {sekcija}-{podsekcija}-{zaporedna številka}">
            Interni ID:
            <span className="rounded-md bg-ink-800 px-2 py-0.5 font-mono text-xs font-bold text-white">{internId}</span>
            {program && <span className="text-xs text-ink-400">(ostane nespremenjen)</span>}
          </div>
          <label className="flex flex-col gap-1 text-sm font-semibold text-ink-700">
            Ime programa
            <input
              autoFocus
              value={naziv}
              maxLength={120}
              onChange={(e) => setNaziv(e.target.value)}
              title="Kratko ime programa navodil"
              className={`${POLJE} h-10`}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm font-semibold text-ink-700">
            Opis programa
            <textarea
              value={opis}
              rows={5}
              onChange={(e) => setOpis(e.target.value)}
              title="Daljši opis programa navodil"
              className={`${POLJE} py-2 font-normal`}
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <MultiSelect
              label="Družine artiklov"
              options={druzinaOpcije.map((o) => o.label)}
              value={druzine.map((id) => druzinaOpcije.find((o) => o.id === id)?.label ?? "")}
              onChange={(v) => setDruzine(druzinaOpcije.filter((o) => v.includes(o.label)).map((o) => o.id))}
              hint="Izberi družine artiklov programa"
            />
            <MultiSelect
              label="Sekcije / podsekcije"
              options={podOpcije.map((o) => o.label)}
              value={podsekcije.map(podLabel)}
              onChange={(v) => {
                // vrstni red izbire ohranimo - prva podsekcija določa interni ID
                const ids = podOpcije.filter((o) => v.includes(o.label)).map((o) => o.id);
                setPodsekcije([...podsekcije.filter((id) => ids.includes(id)), ...ids.filter((id) => !podsekcije.includes(id))]);
              }}
              hint="Izberi sekcije in podsekcije programa"
            />
          </div>
          {kopija && (
            <div className="flex items-center gap-2 rounded-lg bg-sync-50 px-3 py-2 text-sm text-sync-600">
              <Copy className="h-4 w-4 shrink-0" aria-hidden />
              <span className="flex-1">
                Kopija programa <strong className="font-mono">{kopija.interni_id}</strong> - {kopija.naziv} - kopirajo se priprava delovnega mesta in {kopija.stKorakov} korakov s slikami
              </span>
              <button type="button" title="Ne kopiraj korakov" onClick={() => setKopija(null)} className="text-ink-500 hover:text-nok-500">
                <X className="h-4 w-4" aria-hidden />
              </button>
            </div>
          )}
          {napaka && <ErrorText>{napaka}</ErrorText>}
          <div className="flex flex-wrap justify-end gap-2 border-t border-ink-100 pt-4">
            {!program && (
              <Button
                hint="Izberi obstoječi program in kopiraj korake"
                variant="primary"
                icon={Copy}
                className="mr-auto"
                disabled={!programi.length}
                onClick={() => setIzbiram(true)}
              >
                Kopiraj iz obstoječega
              </Button>
            )}
            <Button hint="Zapri okno brez shranjevanja" variant="neutral" icon={X} onClick={onClose}>
              Prekliči
            </Button>
            <Button
              hint={program ? "Shrani spremembe programa" : "Dodaj nov program navodil"}
              variant="success"
              icon={program ? Save : Plus}
              disabled={shranjujem}
              onClick={shrani}
            >
              {shranjujem ? "Shranjujem ..." : program ? "Shrani" : "Dodaj"}
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
