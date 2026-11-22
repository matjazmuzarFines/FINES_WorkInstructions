import { Box } from "lucide-react";

/**
 * Sličica modela iz STEP (modeli/<id>/slika.png). Brez sličice siv okvir z ikono.
 * Velikosti: "tabela" (stolpec Model v Pregledu), "velika" (glava Primerjave).
 */
export function SlikaModela({ src, naziv, velikost = "tabela" }: { src: string | null; naziv: string; velikost?: "tabela" | "velika" }) {
  const okvir = velikost === "tabela" ? "h-14 w-[4.5rem]" : "aspect-[4/3] w-full max-w-[16rem]";
  return (
    <span
      className={`flex shrink-0 items-center justify-center overflow-hidden rounded-lg border border-ink-200 bg-ink-50 ${okvir}`}
      title={src ? `${naziv} - sličica iz STEP` : "Sličice iz STEP še ni"}
    >
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element -- sličica z lokalnega API ali podpisan URL Supabase
        <img src={src} alt={`Sličica ${naziv}`} loading="lazy" className="h-full w-full object-cover" />
      ) : (
        <Box className={velikost === "tabela" ? "h-6 w-6 text-ink-300" : "h-10 w-10 text-ink-300"} aria-hidden />
      )}
    </span>
  );
}
