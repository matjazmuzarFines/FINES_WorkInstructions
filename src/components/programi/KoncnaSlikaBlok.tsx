"use client";

import { useRef, useState } from "react";
import { ImagePlus, Loader2, PackageCheck, Pencil, RefreshCw, Trash2 } from "lucide-react";
import { nastaviKoncnoSliko, odstraniKoncnoSliko, prenesiKoncnoSliko, type Program } from "@/lib/navodila";
import { IconButton } from "@/components/ui/Button";
import { Tabla } from "@/components/ui/Tabla";
import { useToast } from "@/components/ui/Toast";

/**
 * Končna slika proizvoda (desno od priprave delovnega mesta): naloži, zamenjaj, uredi v slikarju, izbriši.
 * Slika se prikazuje na karticah navodil in v glavi navodila.
 */
export function KoncnaSlikaBlok({ program, onSprememba }: { program: Program; onSprememba: (p: Program) => void }) {
  const notify = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [delam, setDelam] = useState(false);
  const [nadOknom, setNadOknom] = useState(false);
  const [tabla, setTabla] = useState<Blob | null>(null);

  async function izvedi(akcija: () => Promise<Program>, sporocilo: string) {
    setDelam(true);
    try {
      onSprememba(await akcija());
      notify("success", sporocilo);
      return true;
    } catch (e) {
      notify("error", (e as Error).message);
      return false;
    } finally {
      setDelam(false);
    }
  }

  const nalozi = (f: File | undefined) => {
    if (f?.type.startsWith("image/")) izvedi(() => nastaviKoncnoSliko(program, f), "Končna slika je shranjena.");
  };

  return (
    <div className="fp-card flex flex-col gap-2 p-3 sm:p-4">
      <div className="flex items-center gap-2">
        <PackageCheck className="h-5 w-5 shrink-0 text-fines-500" aria-hidden />
        <h3 className="text-sm font-bold leading-tight text-ink-900">Končna slika proizvoda</h3>
      </div>

      {program.koncnaUrl ? (
        <div className="relative overflow-hidden rounded-lg border border-ink-200 bg-ink-100">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={program.koncnaUrl} alt={`Končni proizvod - ${program.naziv}`} className="aspect-square w-full object-contain" />
          <div className="absolute inset-x-1 bottom-1 flex justify-center gap-1">
            <IconButton
              hint="Uredi končno sliko v slikarju"
              variant="primary"
              icon={Pencil}
              delam={delam}
              disabled={delam}
              onClick={async () => {
                setDelam(true);
                try {
                  setTabla(await prenesiKoncnoSliko(program));
                } catch (e) {
                  notify("error", (e as Error).message);
                } finally {
                  setDelam(false);
                }
              }}
            />
            <IconButton hint="Zamenjaj končno sliko z novo" variant="primary" icon={RefreshCw} disabled={delam} onClick={() => fileRef.current?.click()} />
            <IconButton
              hint="Izbriši končno sliko proizvoda"
              variant="danger"
              icon={Trash2}
              disabled={delam}
              onClick={() => {
                if (window.confirm("Izbrišem končno sliko proizvoda?")) izvedi(() => odstraniKoncnoSliko(program), "Končna slika je izbrisana.");
              }}
            />
          </div>
        </div>
      ) : (
        <button
          type="button"
          title="Naloži sliko zaključenega proizvoda"
          disabled={delam}
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setNadOknom(true);
          }}
          onDragLeave={() => setNadOknom(false)}
          onDrop={(e) => {
            e.preventDefault();
            setNadOknom(false);
            nalozi(e.dataTransfer.files[0]);
          }}
          className={`flex aspect-square w-full flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed p-2 text-center text-xs font-semibold transition-colors disabled:cursor-wait ${
            nadOknom ? "border-fines-500 bg-fines-50 text-fines-600" : "border-ink-300 bg-ink-50 text-ink-500 hover:border-ink-400 hover:bg-ink-100"
          }`}
        >
          {delam ? <Loader2 className="h-7 w-7 animate-spin text-sync-500" aria-hidden /> : <ImagePlus className="h-7 w-7" aria-hidden />}
          Naloži sliko
          <span className="font-normal">klikni ali povleci sem</span>
        </button>
      )}

      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          nalozi(e.target.files?.[0]);
          e.target.value = "";
        }}
      />

      {tabla && (
        <Tabla
          naslov={`Končna slika - ${program.naziv}`}
          ozadje={tabla}
          onClose={() => setTabla(null)}
          onShrani={async (png) => {
            if (await izvedi(() => nastaviKoncnoSliko(program, png), "Urejena končna slika je shranjena.")) setTabla(null);
          }}
        />
      )}
    </div>
  );
}
