"use client";

import { useCallback, useEffect, useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import {
  naloziPrograme,
  naloziSifrante,
  odstraniProgram,
  posodobiProgram,
  ustvariProgram,
  type Program,
  type ProgramVnos,
  type Sifranti,
} from "@/lib/navodila";
import { lahkoZapustim } from "@/lib/neshranjeno";
import { Button } from "@/components/ui/Button";
import { ErrorText, Loading } from "@/components/ui/Notice";
import { useToast } from "@/components/ui/Toast";
import { ProgramSeznam } from "./ProgramSeznam";
import { ProgramOkno } from "./ProgramOkno";
import { KorakiUrejevalnik } from "./KorakiUrejevalnik";

/** Admin - Programi: levo seznam programov, desno oblikovalec korakov izbranega programa. */
export function Programi() {
  const notify = useToast();
  const [programi, setProgrami] = useState<Program[] | null>(null);
  const [sifranti, setSifranti] = useState<Sifranti | null>(null);
  const [napaka, setNapaka] = useState<string | null>(null);
  const [izbran, setIzbran] = useState<number | null>(null);
  const [okno, setOkno] = useState<"nov" | "uredi" | null>(null);

  const uporabi = useCallback(([p, s]: [Program[], Sifranti]) => {
    setProgrami(p);
    setSifranti(s);
  }, []);
  const nalozi = async () => uporabi(await Promise.all([naloziPrograme(), naloziSifrante()]));

  useEffect(() => {
    Promise.all([naloziPrograme(), naloziSifrante()]).then(uporabi, (e: Error) => setNapaka(e.message));
  }, [uporabi]);

  if (napaka) return <ErrorText>{napaka}</ErrorText>;
  if (!programi || !sifranti) return <Loading />;

  const program = programi.find((p) => p.id === izbran) ?? null;

  async function shrani(vnos: ProgramVnos, kopirajIz?: number) {
    if (okno === "uredi" && program) {
      await posodobiProgram(program.id, vnos);
      notify("success", "Program je shranjen.");
    } else {
      const id = await ustvariProgram(vnos, sifranti!, kopirajIz);
      setIzbran(id);
      notify("success", kopirajIz ? "Program je dodan, koraki so kopirani." : "Program je dodan.");
    }
    setOkno(null);
    await nalozi();
  }

  async function odstrani() {
    if (!program) return;
    if (!window.confirm(`Odstranim program ${program.interni_id} - ${program.naziv}?`)) return;
    try {
      await odstraniProgram(program.id);
      setIzbran(null);
      notify("success", "Program je odstranjen.");
      await nalozi();
    } catch (e) {
      notify("error", (e as Error).message);
    }
  }

  return (
    <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] 2xl:grid-cols-[minmax(0,3fr)_minmax(0,7fr)]">
      <div className="lg:sticky lg:top-20">
        <ProgramSeznam
          naslov="Programi"
          programi={programi}
          sifranti={sifranti}
          izbran={izbran}
          onIzberi={(id) => {
            if (id !== izbran && lahkoZapustim()) setIzbran(id);
          }}
          gumbi={
            <>
              <Button hint="Dodaj nov program navodil" variant="success" icon={Plus} onClick={() => setOkno("nov")}>
                Dodaj
              </Button>
              <Button
                hint="Uredi ime, opis in družine programa"
                variant="primary"
                icon={Pencil}
                disabled={!program}
                onClick={() => setOkno("uredi")}
              >
                <span className="hidden sm:inline">Uredi</span>
              </Button>
              <Button hint="Odstrani izbrani program" variant="danger" icon={Trash2} disabled={!program} onClick={odstrani}>
                <span className="hidden sm:inline">Odstrani</span>
              </Button>
            </>
          }
        />
      </div>

      {program ? (
        <KorakiUrejevalnik
          key={program.id}
          program={program}
          sifranti={sifranti}
          onProgram={(np) => setProgrami((ps) => ps?.map((p) => (p.id === np.id ? np : p)) ?? ps)}
          onStKorakov={(n) => setProgrami((ps) => ps?.map((p) => (p.id === program.id ? { ...p, stKorakov: n } : p)) ?? ps)}
        />
      ) : (
        <div className="fp-card flex min-h-64 flex-col items-center justify-center gap-2 p-8 text-center text-ink-500">
          <p className="font-semibold">Izberi program na seznamu ali dodaj novega.</p>
          <p className="text-sm">Tukaj se nato sestavljajo koraki navodila.</p>
        </div>
      )}

      {okno && (
        <ProgramOkno
          program={okno === "uredi" ? program : null}
          programi={programi}
          sifranti={sifranti}
          onClose={() => setOkno(null)}
          onShrani={shrani}
        />
      )}
    </div>
  );
}
