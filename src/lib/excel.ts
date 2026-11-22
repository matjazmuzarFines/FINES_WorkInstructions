// Izvoz tabel v Excel (enako kot FINES_Production: en list = ena tabela, kot je na zaslonu).
// Knjižnica xlsx se naloži šele ob kliku.

type Celica = string | number | null;
export type ExcelList = { ime: string; vrstice: Record<string, Celica>[] };

/** Ime datoteke samo z ASCII znaki (č -> c ...). */
export const asciiIme = (t: string) =>
  t
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^A-Za-z0-9_-]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/_$/, "");

export async function prenesiXlsx(listi: ExcelList[], ime: string) {
  const XLSX = await import("xlsx");
  const wb = XLSX.utils.book_new();
  for (const l of listi) {
    const ws = l.vrstice.length ? XLSX.utils.json_to_sheet(l.vrstice) : XLSX.utils.aoa_to_sheet([["Ni vrstic"]]);
    XLSX.utils.book_append_sheet(wb, ws, l.ime.replace(/[\\/?*[\]:]/g, " ").slice(0, 31));
  }
  XLSX.writeFile(wb, `${asciiIme(ime)}.xlsx`);
}

/** Danes kot 2026-11-22 (za ime datoteke). */
export const danesIso = () => new Date().toISOString().slice(0, 10);
