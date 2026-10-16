import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const key =
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ??
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export const supabaseConfigured = Boolean(url && key);

let client: SupabaseClient | null = null;
let adminClient: SupabaseClient | null = null;

/** Prijava v aplikacijo (isti uporabniki kot FINES_Production, npr. fines@fines.si). */
export function getSupabase(): SupabaseClient {
  if (!supabaseConfigured) {
    throw new Error(
      "Supabase ni nastavljen. Dodaj NEXT_PUBLIC_SUPABASE_URL in NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY v .env.local.",
    );
  }
  client ??= createClient(url!, key!);
  return client;
}

/**
 * Ločena seja za admin dostop (npr. admin@fines.si). Shranjena je samo v tem zavihku
 * (sessionStorage), osnovna prijava ostane. Po odjavi admina aplikacija dela naprej z osnovno prijavo.
 */
export function getAdminSupabase(): SupabaseClient {
  getSupabase();
  adminClient ??= createClient(url!, key!, {
    auth: {
      storageKey: "wi-admin-auth",
      storage: typeof window === "undefined" ? undefined : window.sessionStorage,
    },
  });
  return adminClient;
}

let adminAktiven = false;

/** Nastavi AdminProvider, ko se admin prijavi / odjavi. */
export function nastaviAdmina(aktiven: boolean) {
  adminAktiven = aktiven;
}

/** Odjemalec za delo s podatki: med admin dostopom admin seja (sme pisati), sicer osnovna. */
export function db(): SupabaseClient {
  return adminAktiven ? getAdminSupabase() : getSupabase();
}

export const SLIKE_BUCKET = "wi_slike";

type Stran<T> = PromiseLike<{ data: T[] | null; error: { message: string } | null }>;

/** Prebere vse vrstice (Supabase vrne največ 1000 vrstic na zahtevo). */
export async function fetchAll<T>(stran: (from: number, to: number) => Stran<T>, velikost = 1000): Promise<T[]> {
  const vse: T[] = [];
  for (let from = 0; ; from += velikost) {
    const { data, error } = await stran(from, from + velikost - 1);
    if (error) throw new Error(error.message);
    vse.push(...(data ?? []));
    if (!data || data.length < velikost) return vse;
  }
}

/** Razdeli seznam na kose (za vpis velikega števila vrstic). */
export function kosi<T>(arr: T[], velikost = 500): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < arr.length; i += velikost) out.push(arr.slice(i, i + velikost));
  return out;
}

/** Napaka Supabase -> Error s slovenskim opisom za pogoste primere. */
export function napaka(e: { message: string; code?: string } | null): void {
  if (!e) return;
  if (e.code === "42501" || /row-level security/i.test(e.message)) {
    throw new Error("Ni dovoljenja - potreben je admin dostop.");
  }
  if (e.code === "42P01" || /does not exist|schema cache/i.test(e.message)) {
    throw new Error("Tabela v bazi ne obstaja - zaženi migracijo supabase/migrations/001_schema.sql.");
  }
  throw new Error(e.message);
}
