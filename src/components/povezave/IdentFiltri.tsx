"use client";

import { useState, type ReactNode } from "react";
import { RotateCcw } from "lucide-react";
import { besedeIskanja, ujemaIskanje } from "@/lib/iskanje";
import { Button } from "@/components/ui/Button";
import { FilterIskanje, FilterPolje, FilterVrstica } from "@/components/ui/Filtri";
import { MultiSelect } from "@/components/ui/MultiSelect";

/** Polja identa, po katerih se filtrira (šifrant in povezani identi). */
export type IdentPolja = { sifra: string; naziv: string | null; klasifikat: string | null; status: string | null };

export const BREZ_STATUSA = "(brez statusa)";
/** Privzeto skriti statusi pri izbiri identov (lahko jih vklopi uporabnik). */
const SKRITI_STATUSI = ["NEAKTIVEN", "IZLOČEN"];

export const statusOf = (i: Pick<IdentPolja, "status">) => i.status?.trim() || BREZ_STATUSA;
export const klasOf = (i: Pick<IdentPolja, "klasifikat">) => i.klasifikat ?? "";

const abc = (a: string, b: string) => a.localeCompare(b, "sl");

/** Možnosti za izbirna filtra (vsi klasifikati in statusi v seznamu). */
export function opcijeIdentov(seznam: IdentPolja[]) {
  return {
    klasifikati: [...new Set(seznam.map(klasOf))].filter(Boolean).sort(),
    statusi: [...new Set(seznam.map(statusOf))].sort(abc),
  };
}

/** Privzeti filtri za izbiro identov: klasifikati 096-111, brez statusov NEAKTIVEN in IZLOČEN. */
export function privzetiFiltriIdentov(seznam: IdentPolja[]) {
  const o = opcijeIdentov(seznam);
  return {
    klasifikati: o.klasifikati.filter((k) => k >= "096" && k <= "111"),
    statusi: o.statusi.filter((s) => !SKRITI_STATUSI.includes(s)),
  };
}

/** Stanje filtrov identov (iskanje, ident, naziv, klasifikat, status). */
export function useIdentFiltri() {
  const [iskanje, setIskanje] = useState("");
  const [ident, setIdent] = useState("");
  const [naziv, setNaziv] = useState("");
  const [klasifikati, setKlasifikati] = useState<string[]>([]);
  const [statusi, setStatusi] = useState<string[]>([]);

  return {
    iskanje,
    setIskanje,
    ident,
    setIdent,
    naziv,
    setNaziv,
    klasifikati,
    setKlasifikati,
    statusi,
    setStatusi,
    /** Ključ vseh filtrov (za ponastavitev strani ob spremembi). */
    kljuc: [iskanje, ident, naziv, klasifikati.join(), statusi.join()].join("|"),
    imaFilter: !!(iskanje || ident || naziv || klasifikati.length || statusi.length),
    /** Počisti besedilne filtre, izbirna nastavi na podane vrednosti (privzeto prazno = vsi). */
    ponastavi(izbira: { klasifikati: string[]; statusi: string[] } = { klasifikati: [], statusi: [] }) {
      setIskanje("");
      setIdent("");
      setNaziv("");
      setKlasifikati(izbira.klasifikati);
      setStatusi(izbira.statusi);
    },
    /** Vrstice, ki ustrezajo filtrom (delno iskanje: vse besede, poljuben vrstni red). */
    filtriraj<T>(vrstice: T[], polja: (v: T) => IdentPolja): T[] {
      const q = besedeIskanja(iskanje);
      const qi = besedeIskanja(ident);
      const qn = besedeIskanja(naziv);
      const kSet = new Set(klasifikati);
      const sSet = new Set(statusi);
      return vrstice.filter((v) => {
        const i = polja(v);
        if (!ujemaIskanje(`${i.sifra} ${i.naziv ?? ""}`, q)) return false;
        if (!ujemaIskanje(i.sifra, qi)) return false;
        if (!ujemaIskanje(i.naziv, qn)) return false;
        if (kSet.size && !kSet.has(klasOf(i))) return false;
        if (sSet.size && !sSet.has(statusOf(i))) return false;
        return true;
      });
    },
  };
}

export type IdentFiltriStanje = ReturnType<typeof useIdentFiltri>;

/** Vrstica filtrov identov (enaka v tabeli povezav in v oknu Dodaj povezavo). */
export function IdentFiltriVrstica({
  f,
  opcije,
  onPonastavi,
  children,
}: {
  f: IdentFiltriStanje;
  opcije: { klasifikati: string[]; statusi: string[] };
  onPonastavi: () => void;
  /** Dodatni filtri (npr. Izbor). */
  children?: ReactNode;
}) {
  return (
    <FilterVrstica>
      <FilterIskanje
        value={f.iskanje}
        onChange={f.setIskanje}
        placeholder="npr. fbm cl ..."
        hint="Vse vpisane besede, poljuben vrstni red"
        className="w-full sm:w-56"
      />
      <FilterIskanje label="Ident" value={f.ident} onChange={f.setIdent} placeholder="npr. 100-601" hint="Filtriraj po identu" className="w-full sm:w-36" />
      <FilterIskanje label="Naziv" value={f.naziv} onChange={f.setNaziv} placeholder="npr. peč cl" hint="Naziv vsebuje vse vpisane besede" className="w-full sm:w-44" />
      <div className="w-full sm:w-40">
        <MultiSelect label="Klasifikat" options={opcije.klasifikati} value={f.klasifikati} onChange={f.setKlasifikati} hint="Prikaži izbrane klasifikate (npr. 096-111)" />
      </div>
      <div className="w-full sm:w-48">
        <MultiSelect label="Status" options={opcije.statusi} value={f.statusi} onChange={f.setStatusi} hint="Prikaži artikle izbranih statusov" />
      </div>
      {children}
      <FilterPolje>
        <Button hint="Ponastavi filtre na privzete" variant="neutral" icon={RotateCcw} onClick={onPonastavi}>
          Ponastavi
        </Button>
      </FilterPolje>
    </FilterVrstica>
  );
}
