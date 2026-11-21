"use client";

import { useRef, useState, type FormEvent } from "react";
import { Plus, UploadCloud, X } from "lucide-react";
import { ustvariModel } from "@/lib/treningApi";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ErrorText } from "@/components/ui/Notice";
import { velikost } from "./oblika";

const POLJE =
  "h-10 w-full rounded-lg border border-ink-200 px-3 text-sm font-normal focus:border-fines-500 focus:outline-none focus:ring-2 focus:ring-fines-100";

/** "Omara FBM-40S" -> "omara-fbm-40s" */
const vId = (s: string) =>
  s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);

/** Nov model za trening: mapa trening/modeli/<id>/ z model.json, STEP datoteke gredo v vhod/. */
export function NovModelOkno({ open, onClose, onUstvarjen }: { open: boolean; onClose: () => void; onUstvarjen: (id: string) => void }) {
  const [naziv, setNaziv] = useState("");
  const [id, setId] = useState("");
  const [idRocno, setIdRocno] = useState(false);
  const [opis, setOpis] = useState("");
  const [datoteke, setDatoteke] = useState<File[]>([]);
  const [nadOknom, setNadOknom] = useState(false);
  const [delam, setDelam] = useState(false);
  const [napaka, setNapaka] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);

  const dodaj = (f: FileList | null) => f && setDatoteke((d) => [...d, ...Array.from(f).filter((x) => !d.some((y) => y.name === x.name))]);

  async function poslji(e: FormEvent) {
    e.preventDefault();
    setDelam(true);
    setNapaka(null);
    try {
      await ustvariModel(id, naziv, opis, datoteke);
      onUstvarjen(id);
      setNaziv("");
      setId("");
      setIdRocno(false);
      setOpis("");
      setDatoteke([]);
    } catch (err) {
      setNapaka((err as Error).message);
    } finally {
      setDelam(false);
    }
  }

  return (
    <Modal open={open} title="Nov model za trening" onClose={onClose}>
      <form onSubmit={poslji} className="flex flex-col gap-3">
        <label className="flex flex-col gap-1 text-xs font-semibold text-ink-600">
          Naziv
          <input
            required
            value={naziv}
            onChange={(e) => {
              setNaziv(e.target.value);
              if (!idRocno) setId(vId(e.target.value));
            }}
            title="Naziv sestava, npr. Omara FBM-40S"
            className={POLJE}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold text-ink-600">
          ID (ime mape)
          <input
            required
            value={id}
            pattern="[a-z0-9][a-z0-9_\-]{0,63}"
            onChange={(e) => {
              setIdRocno(true);
              setId(e.target.value.toLowerCase());
            }}
            title="Ime mape: male črke, številke, pomišljaj"
            className={`${POLJE} font-mono`}
          />
          <span className="font-normal text-ink-400">trening/modeli/{id || "..."}/</span>
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold text-ink-600">
          Opis za AI (neobvezno)
          <textarea
            value={opis}
            onChange={(e) => setOpis(e.target.value)}
            rows={3}
            title="Kaj je sestav, kaj je znano o montaži"
            placeholder="Kaj je sestav, kaj je znano o montaži, na kaj naj bo AI pozoren ..."
            className="rounded-lg border border-ink-200 p-3 text-sm font-normal focus:border-fines-500 focus:outline-none focus:ring-2 focus:ring-fines-100"
          />
        </label>

        <div>
          <div className="mb-1 text-xs font-semibold text-ink-600">3D model (STEP) in priloge</div>
          <button
            type="button"
            title="Izberi STEP datoteko ali jo povleci sem"
            onClick={() => input.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setNadOknom(true);
            }}
            onDragLeave={() => setNadOknom(false)}
            onDrop={(e) => {
              e.preventDefault();
              setNadOknom(false);
              dodaj(e.dataTransfer.files);
            }}
            className={`flex w-full items-center gap-3 rounded-lg border-2 px-4 py-4 text-left text-sm ${
              nadOknom ? "border-fines-500 bg-fines-50" : "border-dashed border-ink-300 bg-ink-100 hover:border-ink-400"
            }`}
          >
            <UploadCloud className="h-6 w-6 shrink-0 text-ink-400" aria-hidden />
            <span className="text-ink-600">Povleci .step / .stp sem ali klikni. Datoteke ostanejo samo na tem računalniku (vhod/).</span>
          </button>
          <input ref={input} type="file" multiple hidden onChange={(e) => dodaj(e.target.files)} />
          {datoteke.length > 0 && (
            <ul className="mt-2 divide-y divide-ink-100 rounded-lg border border-ink-200 text-sm">
              {datoteke.map((d) => (
                <li key={d.name} className="flex items-center justify-between gap-2 px-3 py-1.5">
                  <span className="min-w-0 truncate">{d.name}</span>
                  <span className="flex shrink-0 items-center gap-2 text-xs text-ink-500">
                    {velikost(d.size)}
                    <button
                      type="button"
                      title={`Odstrani ${d.name} s seznama`}
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
        </div>

        {napaka && <ErrorText>{napaka}</ErrorText>}
        <div className="flex justify-end gap-2">
          <Button variant="neutral" hint="Zapri okno brez shranjevanja" onClick={onClose}>
            Prekliči
          </Button>
          <Button type="submit" variant="success" icon={Plus} hint="Ustvari mapo modela in shrani datoteke" disabled={delam || !id || !naziv}>
            {delam ? "Shranjujem ..." : "Dodaj model"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
