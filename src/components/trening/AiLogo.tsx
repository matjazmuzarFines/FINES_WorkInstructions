import { AI_JI, type AiKoda } from "@/lib/trening";

/** Logotip AI-ja (ChatGPT za Astro, Claude za Fable) - povsod namesto črke A / F. */
export const LOGO_AI: Record<AiKoda, { src: string; ime: string }> = {
  astra: { src: "/ai/chatgpt.svg", ime: "ChatGPT" },
  fable: { src: "/ai/claude.svg", ime: "Claude" },
};

export function AiLogo({ ai, className = "h-5 w-5" }: { ai: AiKoda; className?: string }) {
  const naziv = AI_JI.find((a) => a.koda === ai)?.naziv ?? ai;
  return (
    // eslint-disable-next-line @next/next/no-img-element -- majhen statičen SVG
    <img src={LOGO_AI[ai].src} alt={`${LOGO_AI[ai].ime} - ${naziv}`} className={`shrink-0 object-contain ${className}`} />
  );
}
