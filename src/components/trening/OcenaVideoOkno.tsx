"use client";

import { useRef } from "react";
import type { Ocena } from "@/lib/trening";
import { lahkoZapustim } from "@/lib/neshranjeno";
import { Modal } from "@/components/ui/Modal";
import { OcenaObrazec } from "./OcenaObrazec";

/**
 * Ocenjevanje ob videu: velik video (nadaljuje, kjer je bil ustavljen) in obrazec za oceno v istem oknu.
 * Na širokem zaslonu sta drug ob drugem, sicer je video zgoraj in ostane viden med pisanjem.
 */
export function OcenaVideoOkno({
  open,
  naslov,
  video,
  poster,
  zacetek,
  ocena,
  onShrani,
  onClose,
}: {
  open: boolean;
  naslov: string;
  video: string;
  poster?: string;
  /** Sekunda, od katere se video nadaljuje. */
  zacetek: number;
  ocena: Ocena | undefined;
  onShrani: (o: Ocena) => Promise<void>;
  onClose: (cas: number) => void;
}) {
  const ref = useRef<HTMLVideoElement>(null);

  function zapri() {
    if (!lahkoZapustim()) return;
    onClose(ref.current?.currentTime ?? zacetek);
  }

  return (
    <Modal open={open} title={naslov} onClose={zapri} sirina="max-w-[96rem]">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_26rem] xl:items-start">
        <div className="sticky top-0 z-10 -mx-1 bg-white px-1 pb-2 xl:static xl:m-0 xl:p-0">
          <video
            ref={ref}
            src={video}
            poster={poster}
            controls
            autoPlay
            playsInline
            title={naslov}
            onLoadedMetadata={(e) => {
              if (zacetek > 0) e.currentTarget.currentTime = zacetek;
            }}
            className="max-h-[45vh] w-full rounded-lg bg-ink-900 object-contain xl:max-h-[72vh]"
          />
        </div>
        <OcenaObrazec ocena={ocena} onShrani={onShrani} video={ref} />
      </div>
    </Modal>
  );
}
