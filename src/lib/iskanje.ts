// Delno iskanje besedila (skupno za vsa iskalna polja).

/** Male črke brez šumnikov / naglasov: "Peč" -> "pec". */
export function normaliziraj(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");
}

/** Besede iskanja (ločene s presledki), že normalizirane. */
export function besedeIskanja(iskanje: string): string[] {
  return normaliziraj(iskanje).split(/\s+/).filter(Boolean);
}

/**
 * Ali besedilo vsebuje VSE besede iskanja, v poljubnem vrstnem redu in kjerkoli
 * (tudi znotraj besed): "fbm cl" najde "Peč konvekcijska FBM-40S CL".
 * Prazno iskanje ustreza vsemu.
 */
export function ujemaIskanje(besedilo: string | null | undefined, iskanje: string | string[]): boolean {
  const besede = typeof iskanje === "string" ? besedeIskanja(iskanje) : iskanje;
  if (!besede.length) return true;
  const b = normaliziraj(besedilo ?? "");
  return besede.every((w) => b.includes(w));
}
