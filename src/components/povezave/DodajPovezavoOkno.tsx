"use client";

import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { ChevronsDown, Save, X } from "lucide-react";
import { naloziVseIdente, type Ident, type PovezavaIdent, type Program } from "@/lib/navodila";
import { Button } from "@/components/ui/Button";
import { FilterPreklopnik } from "@/components/ui/Filtri";
import { Modal } from "@/components/ui/Modal";
import { ErrorText, Loading } from "@/components/ui/Notice";
import { SortTh, useRazvrscanje } from "@/components/ui/Tabela";
import { IdentFiltriVrstica, opcijeIdentov, privzetiFiltriIdentov, statusOf, useIdentFiltri } from "./IdentFiltri";

type Kljuc = "sifra" | "naziv" | "klasifikat" | "status";
type Izbor = "vsi" | "izbrani" | "neizbrani";

const STRAN = 200;

/**
 * Okno za povezovanje identov s programom: tabela šifranta s checkboxi in filtri za vse stolpce.
 * Že povezani identi so pokljukani; odkljukan povezan ident se ob shranjevanju odstrani.
 */
export function DodajPovezavoOkno({
  program,
  povezave,
  onClose,
  onShrani,
}: {
  program: Program;
  /** Obstoječe povezave izbranega programa. */
  povezave: PovezavaIdent[];
  onClose: () => void;
  onShrani: (dodaj: string[], odstrani: number[]) => Promise<void>;
}) {
  const [identi, setIdenti] = useState<Ident[] | null>(null);
  const [napaka, setNapaka] = useState<string | null>(null);
  const povezani = useMemo(() => new Set(povezave.map((p) => p.ident)), [povezave]);
  const [izbrani, setIzbrani] = useState<Set<string>>(() => new Set(povezave.map((p) => p.ident)));
  const [shranjujem, setShranjujem] = useState(false);
  const [prikazanih, setPrikazanih] = useState(STRAN);

  // filtri (privzeto klasifikati 096-111 brez statusov NEAKTIVEN in IZLOČEN)
  const f = useIdentFiltri();
  const [izbor, setIzbor] = useState<Izbor>("vsi");
  const opcije = useMemo(() => opcijeIdentov(identi ?? []), [identi]);
  const { ponastavi } = f;

  useEffect(() => {
    naloziVseIdente().then(
      (r) => {
        setIdenti(r);
        ponastavi(privzetiFiltriIdentov(r));
      },
      (e: Error) => setNapaka(e.message),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sort = useRazvrscanje<Ident, Kljuc>({
    sifra: (i) => i.sifra,
    naziv: (i) => i.naziv,
    klasifikat: (i) => i.klasifikat,
    status: (i) => i.status,
  });

  const filtrirani = f
    .filtriraj(identi ?? [], (i) => i)
    .filter((i) => (izbor === "izbrani" ? izbrani.has(i.sifra) : izbor === "neizbrani" ? !izbrani.has(i.sifra) : true));

  const razvrsceni = sort.razvrsti(filtrirani);
  const vidni = razvrsceni.slice(0, prikazanih);

  const dodaj = [...izbrani].filter((s) => !povezani.has(s));
  const odstrani = povezave.filter((p) => !izbrani.has(p.ident)).map((p) => p.id);
  const sprememb = dodaj.length + odstrani.length;

  const vsiFiltriraniIzbrani = filtrirani.length > 0 && filtrirani.every((i) => izbrani.has(i.sifra));

  function preklopi(sifra: string) {
    setIzbrani((prej) => {
      const nov = new Set(prej);
      if (nov.has(sifra)) nov.delete(sifra);
      else nov.add(sifra);
      return nov;
    });
  }

  function preklopiVse() {
    setIzbrani((prej) => {
      const nov = new Set(prej);
      for (const i of filtrirani) {
        if (vsiFiltriraniIzbrani) nov.delete(i.sifra);
        else nov.add(i.sifra);
      }
      return nov;
    });
  }

  function zapri() {
    if (sprememb && !window.confirm("Imaš neshranjene spremembe povezav. Jih zavržem?")) return;
    onClose();
  }

  async function shrani() {
    setShranjujem(true);
    try {
      await onShrani(dodaj, odstrani);
    } catch (e) {
      setNapaka((e as Error).message);
      setShranjujem(false);
    }
  }

  // ob spremembi filtrov znova prikaži prvo stran
  const filtriKljuc = `${f.kljuc}|${izbor}`;
  const [zadnjiFiltri, setZadnjiFiltri] = useState(filtriKljuc);
  if (zadnjiFiltri !== filtriKljuc) {
    setZadnjiFiltri(filtriKljuc);
    setPrikazanih(STRAN);
  }

  return (
    <Modal open title={`Dodaj povezavo - ${program.interni_id} ${program.naziv}`} onClose={zapri} sirina="max-w-6xl">
      {napaka && <ErrorText className="mb-3">{napaka}</ErrorText>}
      {!identi ? (
        !napaka && <Loading />
      ) : (
        <div className="flex flex-col gap-3">
          <IdentFiltriVrstica
            f={f}
            opcije={opcije}
            onPonastavi={() => {
              setIzbor("vsi");
              f.ponastavi(privzetiFiltriIdentov(identi));
            }}
          >
            <FilterPreklopnik
              label="Izbor"
              value={izbor}
              onChange={setIzbor}
              options={[
                { value: "vsi", label: "Vsi", hint: "Prikaži izbrane in neizbrane" },
                { value: "izbrani", label: "Izbrani", hint: "Prikaži samo pokljukane idente", stevilo: izbrani.size },
                { value: "neizbrani", label: "Neizbrani", hint: "Prikaži samo nepokljukane idente" },
              ]}
            />
          </IdentFiltriVrstica>

          <p className="text-xs text-ink-500">
            Prikazanih {filtrirani.length.toLocaleString("sl-SI")} od {identi.length.toLocaleString("sl-SI")} šifer · privzeto klasifikati
            096-111 brez statusov NEAKTIVEN in IZLOČEN
          </p>

          <div className="max-h-[50vh] overflow-auto rounded-lg" style={{ "--fp-thead-top": "0px" } as CSSProperties}>
            <table className="w-full text-sm">
              <thead className="fp-thead">
                <tr>
                  <th className="w-10 px-2 py-2">
                    <input
                      type="checkbox"
                      checked={vsiFiltriraniIzbrani}
                      onChange={preklopiVse}
                      title={vsiFiltriraniIzbrani ? "Odkljukaj vse prikazane po filtrih" : "Pokljukaj vse prikazane po filtrih"}
                      className="h-4 w-4 accent-fines-500"
                    />
                  </th>
                  <SortTh sort={sort} kljuc="sifra">
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
                </tr>
              </thead>
              <tbody>
                {vidni.map((i) => {
                  const izbran = izbrani.has(i.sifra);
                  const spremenjen = izbran !== povezani.has(i.sifra);
                  return (
                    <tr
                      key={i.sifra}
                      onClick={() => preklopi(i.sifra)}
                      title={izbran ? "Odkljukaj ident" : "Pokljukaj ident za povezavo"}
                      className={`cursor-pointer border-b border-ink-100 transition-colors ${
                        spremenjen ? (izbran ? "bg-ok-50" : "bg-nok-50") : izbran ? "bg-fines-50" : "hover:bg-ink-50"
                      }`}
                    >
                      <td className="px-2 py-1.5">
                        <input
                          type="checkbox"
                          checked={izbran}
                          onChange={() => preklopi(i.sifra)}
                          onClick={(e) => e.stopPropagation()}
                          aria-label={`Izberi ${i.sifra}`}
                          className="h-4 w-4 accent-fines-500"
                        />
                      </td>
                      <td className="whitespace-nowrap px-2 py-1.5 font-mono text-xs font-semibold">{i.sifra}</td>
                      <td className="px-2 py-1.5">{i.naziv}</td>
                      <td className="px-2 py-1.5 font-mono text-xs">{i.klasifikat}</td>
                      <td className="whitespace-nowrap px-2 py-1.5 text-xs text-ink-600">{statusOf(i)}</td>
                    </tr>
                  );
                })}
                {filtrirani.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-2 py-8 text-center text-sm text-ink-400">
                      Ni šifer za izbrane filtre.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            {razvrsceni.length > prikazanih && (
              <div className="flex justify-center py-3">
                <Button hint="Prikaži naslednjih 200 šifer" variant="neutral" icon={ChevronsDown} onClick={() => setPrikazanih((n) => n + STRAN)}>
                  Prikaži več ({(razvrsceni.length - prikazanih).toLocaleString("sl-SI")})
                </Button>
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-3 border-t border-ink-100 pt-3">
            <span className="flex-1 text-sm text-ink-600">
              {sprememb ? (
                <strong className="text-warn-700">
                  Neshranjene spremembe: {dodaj.length > 0 && <span className="text-ok-600">+{dodaj.length} novih</span>}
                  {dodaj.length > 0 && odstrani.length > 0 && " · "}
                  {odstrani.length > 0 && <span className="text-nok-600">-{odstrani.length} odstranjenih</span>}
                </strong>
              ) : (
                `Povezanih identov: ${povezani.size}`
              )}
            </span>
            <Button hint="Zapri okno brez shranjevanja" variant="neutral" icon={X} onClick={zapri}>
              Prekliči
            </Button>
            <Button hint="Shrani izbrane povezave identov" variant="success" icon={Save} disabled={!sprememb || shranjujem} onClick={shrani}>
              {shranjujem ? "Shranjujem ..." : "Shrani povezave"}
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
