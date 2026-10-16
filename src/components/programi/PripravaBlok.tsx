"use client";

import { useState } from "react";
import { ClipboardList, GripVertical, Plus, Trash2 } from "lucide-react";
import type { Priprava } from "@/lib/navodila";
import { Button, IconButton } from "@/components/ui/Button";

const POLJE =
  "w-full rounded-lg border border-ink-200 bg-white px-3 text-sm focus:border-fines-500 focus:outline-none focus:ring-2 focus:ring-fines-100";

/**
 * Priprava delovnega mesta: alineje dodatne opreme / materiala za program (npr. "Tesnilni trak 20 mm").
 * Nova postavka: vpis + Enter (prilepljen seznam z več vrsticami doda več postavk).
 * Vrstni red: povleci postavko za ročaj. Besedila se shranijo z gumbom Shrani (spodnja vrstica).
 */
export function PripravaBlok({
  postavke,
  spremembe,
  delam,
  onSpremeni,
  onDodaj,
  onOdstrani,
  onRazvrsti,
}: {
  postavke: Priprava[];
  spremembe: Record<number, string>;
  delam: boolean;
  onSpremeni: (p: Priprava, naziv: string) => void;
  onDodaj: (nazivi: string[]) => void;
  onOdstrani: (p: Priprava) => void;
  onRazvrsti: (idji: number[]) => void;
}) {
  const [nova, setNova] = useState("");
  const [vlecem, setVlecem] = useState<number | null>(null);
  const [nad, setNad] = useState<number | null>(null);

  function dodaj(besedilo = nova) {
    const nazivi = besedilo
      .split(/\r?\n/)
      .map((v) => v.replace(/^\s*[-–•*]\s*/, "").trim())
      .filter(Boolean);
    if (!nazivi.length) return;
    onDodaj(nazivi);
    setNova("");
  }

  function spusti(cilj: number) {
    if (vlecem === null || vlecem === cilj) return;
    const iVir = postavke.findIndex((p) => p.id === vlecem);
    const iCilj = postavke.findIndex((p) => p.id === cilj);
    const idji = postavke.map((p) => p.id).filter((id) => id !== vlecem);
    idji.splice(iVir < iCilj ? iCilj : idji.indexOf(cilj), 0, vlecem);
    onRazvrsti(idji);
  }

  return (
    <div className="fp-card flex flex-col gap-3 p-3 sm:p-4">
      <div className="flex items-center gap-2">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-ink-800 text-white">
          <ClipboardList className="h-5 w-5" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="text-base font-bold text-ink-900">Priprava delovnega mesta</h3>
          <p className="text-xs text-ink-500">Dodatna oprema in material, ki ga delavec pripravi pred začetkom ({postavke.length})</p>
        </div>
      </div>

      {postavke.length > 0 && (
        <ul className="flex flex-col gap-1.5">
          {postavke.map((p) => {
            const vrednost = spremembe[p.id] ?? p.naziv;
            return (
              <li
                key={p.id}
                draggable={!delam && postavke.length > 1}
                onDragStart={(e) => {
                  e.dataTransfer.setData("application/x-wi-priprava", String(p.id));
                  e.dataTransfer.effectAllowed = "move";
                  setVlecem(p.id);
                }}
                onDragEnd={() => {
                  setVlecem(null);
                  setNad(null);
                }}
                onDragOver={(e) => {
                  if (vlecem === null) return;
                  e.preventDefault();
                  if (nad !== p.id) setNad(p.id);
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  spusti(p.id);
                  setVlecem(null);
                  setNad(null);
                }}
                className={`flex items-center gap-1.5 rounded-lg transition-colors ${
                  vlecem === p.id ? "opacity-40" : nad === p.id ? "bg-fines-50 outline-2 outline-dashed outline-fines-500" : ""
                }`}
              >
                <span
                  className={`flex h-9 w-6 shrink-0 items-center justify-center text-ink-300 ${postavke.length > 1 ? "cursor-grab hover:text-ink-600 active:cursor-grabbing" : ""}`}
                  title={postavke.length > 1 ? "Povleci za spremembo vrstnega reda" : undefined}
                >
                  {postavke.length > 1 && <GripVertical className="h-4 w-4" aria-hidden />}
                </span>
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-fines-500" aria-hidden />
                <input
                  value={vrednost}
                  onChange={(e) => onSpremeni(p, e.target.value)}
                  title="Opis potrebne opreme ali materiala"
                  className={`${POLJE} h-9 ${spremembe[p.id] !== undefined ? "border-warn-400" : ""}`}
                />
                <IconButton hint="Odstrani postavko iz priprave" variant="danger" icon={Trash2} disabled={delam} onClick={() => onOdstrani(p)} />
              </li>
            );
          })}
        </ul>
      )}

      <div className="flex gap-2">
        <input
          value={nova}
          onChange={(e) => setNova(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              dodaj();
            }
          }}
          onPaste={(e) => {
            const tekst = e.clipboardData.getData("text");
            if (/\r?\n/.test(tekst.trim())) {
              e.preventDefault();
              dodaj(tekst);
            }
          }}
          placeholder='npr. "Tesnilni trak 20 mm" + Enter (ali prilepi seznam)'
          title="Vpiši potrebno opremo in pritisni Enter"
          className={`${POLJE} h-10`}
        />
        <Button hint="Dodaj postavko v pripravo delovnega mesta" variant="success" icon={Plus} disabled={delam || !nova.trim()} onClick={() => dodaj()}>
          <span className="hidden sm:inline">Dodaj</span>
        </Button>
      </div>
    </div>
  );
}
