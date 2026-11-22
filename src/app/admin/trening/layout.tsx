import type { ReactNode } from "react";
import { SamoAdmin } from "@/components/Admin";
import { Trening } from "@/components/trening/Trening";

/**
 * AI trening: /admin/trening = Pregled, /admin/trening/<model> = Primerjava modela.
 * Trening je v layoutu, da ob menjavi pogleda podatki ostanejo naloženi; pogled določa URL (gumb nazaj deluje).
 */
export default function TreningLayout({ children }: { children: ReactNode }) {
  return (
    <SamoAdmin>
      <Trening />
      {children}
    </SamoAdmin>
  );
}
