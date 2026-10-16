"use client";

import { createContext, useContext, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Eye, EyeOff, LogIn, LogOut, ShieldCheck } from "lucide-react";
import type { Session, SupabaseClient } from "@supabase/supabase-js";
import { getAdminSupabase, getSupabase, nastaviAdmina, supabaseConfigured } from "@/lib/supabase";
import { lahkoZapustim } from "@/lib/neshranjeno";
import { Button } from "./ui/Button";
import { Modal } from "./ui/Modal";
import { ErrorText, Loading } from "./ui/Notice";

type AdminStanje = {
  /** Ločena admin seja (null = ni dodatne admin prijave). */
  seja: Session | null;
  admin: boolean;
  /** Admin pravice ima že glavna prijava aplikacije (npr. admin@fines.si). */
  glavniAdmin: boolean;
  /** Še preverjam, ali je glavna prijava admin. */
  preverjam: boolean;
  odpriPrijavo: () => void;
  odjava: () => Promise<void>;
};

const AdminContext = createContext<AdminStanje>({
  seja: null,
  admin: false,
  glavniAdmin: false,
  preverjam: false,
  odpriPrijavo: () => {},
  odjava: async () => {},
});

export const useAdmin = () => useContext(AdminContext);

/** Preveri, ali je uporabnik na seznamu adminov (tabela wi_admini). */
async function jeAdmin(sb: SupabaseClient, email: string): Promise<boolean> {
  const { data, error } = await sb
    .from("wi_admini")
    .select("id")
    .eq("visible", true)
    .ilike("email", email)
    .limit(1);
  if (error) throw new Error(error.message);
  return (data ?? []).length > 0;
}

/**
 * Admin dostop:
 * - če je glavna prijava admin (tabela wi_admini, npr. admin@fines.si), je admin dostop odklenjen takoj,
 * - sicer ločena prijava (popup) poleg osnovne prijave; velja samo v tem zavihku,
 *   odjava admina osnovne prijave ne odjavi.
 */
export function AdminProvider({ email, children }: { email?: string; children: ReactNode }) {
  const [seja, setSeja] = useState<Session | null>(null);
  const [okno, setOkno] = useState(false);
  const [glavniAdmin, setGlavniAdmin] = useState<{ email: string; admin: boolean } | null>(null);

  // glavna prijava: ali je uporabnik admin
  useEffect(() => {
    if (!supabaseConfigured || !email) return;
    let preklicano = false;
    jeAdmin(getSupabase(), email).then(
      (admin) => !preklicano && setGlavniAdmin({ email, admin }),
      () => !preklicano && setGlavniAdmin({ email, admin: false }),
    );
    return () => {
      preklicano = true;
    };
  }, [email]);
  const jeGlavniAdmin = glavniAdmin?.email === email && !!glavniAdmin?.admin;
  const preverjam = !!email && glavniAdmin?.email !== email;

  useEffect(() => {
    if (!supabaseConfigured) return;
    const sb = getAdminSupabase();
    sb.auth.getSession().then(({ data }) => {
      nastaviAdmina(!!data.session);
      setSeja(data.session);
    });
    const { data } = sb.auth.onAuthStateChange((_d, s) => {
      nastaviAdmina(!!s);
      setSeja(s);
    });
    return () => data.subscription.unsubscribe();
  }, []);

  async function odjava() {
    if (!lahkoZapustim()) return;
    nastaviAdmina(false);
    await getAdminSupabase().auth.signOut();
    setSeja(null);
  }

  return (
    <AdminContext.Provider
      value={{ seja, admin: jeGlavniAdmin || !!seja, glavniAdmin: jeGlavniAdmin, preverjam, odpriPrijavo: () => setOkno(true), odjava }}
    >
      {children}
      <AdminOkno open={okno} seja={seja} glavniEmail={jeGlavniAdmin ? email : undefined} onClose={() => setOkno(false)} onOdjava={odjava} />
    </AdminContext.Provider>
  );
}

const POLJE =
  "h-10 w-full rounded-lg border border-ink-200 px-3 text-sm focus:border-fines-500 focus:outline-none focus:ring-2 focus:ring-fines-100";

function AdminOkno({
  open,
  seja,
  glavniEmail,
  onClose,
  onOdjava,
}: {
  open: boolean;
  seja: Session | null;
  /** Glavna prijava je admin - dodatna prijava ni potrebna. */
  glavniEmail?: string;
  onClose: () => void;
  onOdjava: () => Promise<void>;
}) {
  const [email, setEmail] = useState("");
  const [geslo, setGeslo] = useState("");
  const [pokazi, setPokazi] = useState(false);
  const [napaka, setNapaka] = useState<string | null>(null);
  const [delam, setDelam] = useState(false);

  async function potrdi(e: FormEvent) {
    e.preventDefault();
    setNapaka(null);
    setDelam(true);
    const sb = getAdminSupabase();
    try {
      const { error } = await sb.auth.signInWithPassword({ email: email.trim(), password: geslo });
      if (error) throw new Error(error.message === "Invalid login credentials" ? "Napačen e-mail ali geslo." : error.message);
      if (!(await jeAdmin(sb, email.trim()))) {
        await sb.auth.signOut();
        throw new Error("Uporabnik nima admin pravic.");
      }
      setGeslo("");
      onClose();
    } catch (err) {
      setNapaka((err as Error).message);
    } finally {
      setDelam(false);
    }
  }

  return (
    <Modal open={open} title="Admin dostop" onClose={onClose} sirina="max-w-sm">
      {glavniEmail ? (
        <div className="flex items-center gap-3 rounded-lg bg-ok-50 px-3 py-3 text-sm text-ok-600">
          <ShieldCheck className="h-5 w-5 shrink-0" aria-hidden />
          <span>
            Prijavljen si kot admin (<strong>{glavniEmail}</strong>) - admin dostop je odklenjen. Za odjavo uporabi Izhod.
          </span>
        </div>
      ) : seja ? (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3 rounded-lg bg-ok-50 px-3 py-3 text-sm text-ok-600">
            <ShieldCheck className="h-5 w-5 shrink-0" aria-hidden />
            <span>
              Prijavljen admin: <strong>{seja.user.email}</strong>
            </span>
          </div>
          <Button
            hint="Zapri admin dostop, ostani prijavljen"
            variant="primary"
            icon={LogOut}
            onClick={async () => {
              await onOdjava();
              onClose();
            }}
          >
            Odjava admina
          </Button>
        </div>
      ) : (
        <form onSubmit={potrdi} className="flex flex-col gap-4">
          <p className="text-sm text-ink-600">Za urejanje navodil se prijavi z admin uporabnikom.</p>
          <label className="flex flex-col gap-1 text-sm font-semibold text-ink-700">
            E-mail
            <input
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              title="Vpiši e-mail admin uporabnika"
              className={POLJE}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm font-semibold text-ink-700">
            Geslo
            <div className="relative">
              <input
                type={pokazi ? "text" : "password"}
                autoComplete="current-password"
                required
                value={geslo}
                onChange={(e) => setGeslo(e.target.value)}
                title="Vpiši admin geslo"
                className={`${POLJE} pr-10`}
              />
              <button
                type="button"
                title={pokazi ? "Skrij geslo" : "Pokaži geslo"}
                aria-label={pokazi ? "Skrij geslo" : "Pokaži geslo"}
                onClick={() => setPokazi(!pokazi)}
                className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-ink-500 hover:text-fines-500"
              >
                {pokazi ? <EyeOff className="h-4 w-4" aria-hidden /> : <Eye className="h-4 w-4" aria-hidden />}
              </button>
            </div>
          </label>
          {napaka && <ErrorText>{napaka}</ErrorText>}
          <Button type="submit" hint="Prijavi se kot admin" icon={LogIn} disabled={delam}>
            {delam ? "Prijavljam ..." : "Prijava"}
          </Button>
        </form>
      )}
    </Modal>
  );
}

/** Vsebina samo za admine; brez admin dostopa pokaže poziv k prijavi. */
export function SamoAdmin({ children }: { children: ReactNode }) {
  const { admin, preverjam, odpriPrijavo } = useAdmin();
  if (admin) return <>{children}</>;
  if (preverjam) return <Loading />;
  return (
    <div className="fp-card mx-auto flex max-w-md flex-col items-center gap-4 p-8 text-center">
      <ShieldCheck className="h-12 w-12 text-fines-500" aria-hidden />
      <div>
        <h2 className="text-xl font-bold text-ink-900">Potreben je admin dostop</h2>
        <p className="mt-1 text-sm text-ink-600">Ta stran je namenjena urejanju navodil.</p>
      </div>
      <Button hint="Odpri prijavo za admin dostop" icon={LogIn} onClick={odpriPrijavo}>
        Admin prijava
      </Button>
    </div>
  );
}
