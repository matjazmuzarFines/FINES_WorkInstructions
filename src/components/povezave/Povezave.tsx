"use client";

import { useEffect, useMemo, useState } from "react";
import { Link2, Trash2 } from "lucide-react";
import {
  naloziPovezave,
  naloziPrograme,
  naloziSifrante,
  odstraniPovezavo,
  odstraniPovezave,
  poveziIdente,
  type PovezavaIdent,
  type Program,
  type Sifranti,
} from "@/lib/navodila";
import { ProgramSeznam } from "@/components/programi/ProgramSeznam";
import { Button, IconButton } from "@/components/ui/Button";
import { ErrorText, Loading } from "@/components/ui/Notice";
import { SortTh, TabelaOkvir, useRazvrscanje } from "@/components/ui/Tabela";
import { useToast } from "@/components/ui/Toast";
import { DodajPovezavoOkno } from "./DodajPovezavoOkno";
import { IdentFiltriVrstica, opcijeIdentov, statusOf, useIdentFiltri, type IdentPolja } from "./IdentFiltri";

type Kljuc = "ident" | "naziv" | "klasifikat" | "status" | "dodano";

const polja = (p: PovezavaIdent): IdentPolja => ({ sifra: p.ident, naziv: p.naziv, klasifikat: p.klasifikat, status: p.status });

/**
 * Admin - Povezave: levo seznam programov, desno povezani identi izbranega programa.
 * Identi se dodajo v oknu "Dodaj povezavo" (tabela šifranta s checkboxi in filtri).
 */
export function Povezave() {
  const notify = useToast();
  const [programi, setProgrami] = useState<Program[] | null>(null);
  const [sifranti, setSifranti] = useState<Sifranti | null>(null);
  const [povezave, setPovezave] = useState<PovezavaIdent[]>([]);
  const [napaka, setNapaka] = useState<string | null>(null);
  const [izbran, setIzbran] = useState<number | null>(null);
  const [okno, setOkno] = useState(false);
  const [delam, setDelam] = useState(false);
  // filtri tabele povezav (enaki kot v oknu Dodaj povezavo; privzeto prikazane vse povezave)
  const f = useIdentFiltri();

  useEffect(() => {
    Promise.all([naloziPrograme(), naloziSifrante(), naloziPovezave()]).then(
      ([p, s, pov]) => {
        setProgrami(p);
        setSifranti(s);
        setPovezave(pov);
      },
      (e: Error) => setNapaka(e.message),
    );
  }, []);

  const sort = useRazvrscanje<PovezavaIdent, Kljuc>({
    ident: (p) => p.ident,
    naziv: (p) => p.naziv,
    klasifikat: (p) => p.klasifikat,
    status: (p) => p.status,
    dodano: (p) => p.created_at,
  });

  const povezaniProgramu = useMemo(() => povezave.filter((p) => p.program_id === izbran), [povezave, izbran]);
  const opcije = useMemo(() => opcijeIdentov(povezaniProgramu.map(polja)), [povezaniProgramu]);

  if (napaka) return <ErrorText>{napaka}</ErrorText>;
  if (!programi || !sifranti) return <Loading />;

  const program = programi.find((p) => p.id === izbran) ?? null;
  const razvrsceni = sort.razvrsti(f.filtriraj(povezaniProgramu, polja));

  async function shraniIzOkna(dodaj: string[], odstrani: number[]) {
    if (!program) return;
    if (dodaj.length) await poveziIdente(program.id, dodaj);
    if (odstrani.length) await odstraniPovezave(odstrani);
    setPovezave(await naloziPovezave());
    setOkno(false);
    notify(
      "success",
      [dodaj.length && `Dodanih povezav: ${dodaj.length}`, odstrani.length && `odstranjenih: ${odstrani.length}`].filter(Boolean).join(", ") + ".",
    );
  }

  async function odstrani(p: PovezavaIdent) {
    if (!window.confirm(`Odstranim povezavo z identom ${p.ident}?`)) return;
    setDelam(true);
    try {
      await odstraniPovezavo(p.id);
      setPovezave(await naloziPovezave());
      notify("success", "Povezava je odstranjena.");
    } catch (e) {
      notify("error", (e as Error).message);
    } finally {
      setDelam(false);
    }
  }

  return (
    <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <div className="lg:sticky lg:top-20">
        <ProgramSeznam naslov="Programi" programi={programi} sifranti={sifranti} izbran={izbran} onIzberi={setIzbran} />
      </div>

      {!program ? (
        <div className="fp-card flex min-h-64 flex-col items-center justify-center gap-2 p-8 text-center text-ink-500">
          <p className="font-semibold">Izberi program na seznamu.</p>
          <p className="text-sm">Nato mu dodaš idente, pri katerih se navodilo odpre po skeniranju.</p>
        </div>
      ) : (
        <section className="fp-card flex min-w-0 flex-col gap-3 p-3 sm:p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-[min(100%,18rem)] flex-1">
              <span className="rounded-md bg-ink-800 px-2 py-0.5 font-mono text-xs font-bold text-white">{program.interni_id}</span>
              <h2 className="mt-1 text-xl font-bold text-ink-900">{program.naziv}</h2>
              <p className="text-sm text-ink-500">
                Povezani identi: {f.imaFilter ? `${razvrsceni.length} / ${povezaniProgramu.length}` : povezaniProgramu.length}
              </p>
            </div>
            <Button hint="Izberi idente iz šifranta za ta program" variant="success" icon={Link2} onClick={() => setOkno(true)}>
              Dodaj povezavo
            </Button>
          </div>

          {povezaniProgramu.length > 0 && <IdentFiltriVrstica f={f} opcije={opcije} onPonastavi={() => f.ponastavi()} />}

          <TabelaOkvir>
            <table className="w-full text-sm">
              <thead className="fp-thead">
                <tr>
                  <SortTh sort={sort} kljuc="ident">
                    Ident
                  </SortTh>
                  <SortTh sort={sort} kljuc="naziv">
                    Naziv
                  </SortTh>
                  <SortTh sort={sort} kljuc="klasifikat">
                    Klasifikat
                  </SortTh>
                  <SortTh sort={sort} kljuc="status">
                    Status
                  </SortTh>
                  <SortTh sort={sort} kljuc="dodano" className="hidden sm:table-cell">
                    Dodano
                  </SortTh>
                  <th className="w-12 px-2 py-2" />
                </tr>
              </thead>
              <tbody>
                {razvrsceni.map((p) => (
                  <tr key={p.id} className="border-b border-ink-100 hover:bg-ink-50">
                    <td className="whitespace-nowrap px-2 py-1.5 font-mono text-xs font-semibold">{p.ident}</td>
                    <td className="px-2 py-1.5">{p.naziv ?? <span className="text-ink-400">ni v šifrantu</span>}</td>
                    <td className="px-2 py-1.5 font-mono text-xs">{p.klasifikat}</td>
                    <td className="whitespace-nowrap px-2 py-1.5 text-xs text-ink-600">{statusOf(p)}</td>
                    <td className="hidden whitespace-nowrap px-2 py-1.5 text-xs text-ink-500 sm:table-cell">
                      {new Date(p.created_at).toLocaleDateString("sl-SI")}
                    </td>
                    <td className="px-2 py-1">
                      <IconButton
                        hint={`Odstrani povezavo z identom ${p.ident}`}
                        variant="danger"
                        icon={Trash2}
                        disabled={delam}
                        onClick={() => odstrani(p)}
                      />
                    </td>
                  </tr>
                ))}
                {razvrsceni.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-2 py-8 text-center text-sm text-ink-400">
                      {povezaniProgramu.length
                        ? "Ni povezav za izbrane filtre."
                        : "Program še ni povezan z nobenim identom. Klikni \"Dodaj povezavo\"."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </TabelaOkvir>
        </section>
      )}

      {okno && program && (
        <DodajPovezavoOkno program={program} povezave={povezaniProgramu} onClose={() => setOkno(false)} onShrani={shraniIzOkna} />
      )}
    </div>
  );
}
