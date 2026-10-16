"use client";

import { useState, type ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ChevronDown, ChevronLeft, Home, Info, LogOut, Menu, Shield, ShieldCheck, X } from "lucide-react";
import { NAV, aktivnaPostavka, findNav, parentHref, type NavGroup, type NavItem, type NavSekcija } from "@/lib/nav";
import { lahkoZapustim } from "@/lib/neshranjeno";
import { odjava, useSeja } from "@/lib/auth";
import { supabaseConfigured } from "@/lib/supabase";
import { APP_VERSION, CHANGELOG } from "@/lib/changelog";
import { Button, IconButton } from "./ui/Button";
import { Modal } from "./ui/Modal";
import { Loading } from "./ui/Notice";
import { Prijava } from "./Prijava";
import { ToastProvider } from "./ui/Toast";
import { AdminProvider, useAdmin } from "./Admin";

export function AppShell({ children }: { children: ReactNode }) {
  const seja = useSeja();

  // Brez prijave aplikacija pokaže samo prijavno okno (podatke ščiti tudi RLS v bazi).
  if (supabaseConfigured && seja === undefined) return <Loading />;
  if (supabaseConfigured && !seja) return <Prijava />;

  return (
    <ToastProvider>
      <AdminProvider email={seja?.user.email}>
        <Okvir email={seja?.user.email}>{children}</Okvir>
      </AdminProvider>
    </ToastProvider>
  );
}

/** Glava, leva navigacija (samo med admin dostopom), vsebina in noga. */
function Okvir({ email, children }: { email?: string; children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { admin, glavniAdmin, seja: adminSeja, odpriPrijavo, odjava: odjavaAdmina } = useAdmin();
  // Meni je odprt samo na strani, kjer je bil odprt -> ob menjavi strani se zapre.
  const [menuOdprtNa, setMenuOdprtNa] = useState<string | null>(null);
  const menuOpen = admin && menuOdprtNa === pathname;
  const setMenuOpen = (open: boolean) => setMenuOdprtNa(open ? pathname : null);
  const [infoOpen, setInfoOpen] = useState(false);
  // Ročno razprti moduli menija; modul trenutne strani je vedno razprt.
  const [odprtiModuli, setOdprtiModuli] = useState<Set<string>>(new Set());

  const isHome = pathname === "/";
  const current = findNav(pathname);
  const title = current
    ? [current.group.label, current.item.label, current.sub?.label].filter(Boolean).join(" · ")
    : pathname.startsWith("/navodila/")
      ? "Navodila"
      : "Skeniranje naloga";

  function preklopiModul(label: string, prikazan: boolean) {
    setOdprtiModuli((prej) => {
      const nov = new Set(prej);
      if (prikazan) nov.delete(label);
      else nov.add(label);
      return nov;
    });
  }

  function nazaj() {
    if (lahkoZapustim()) router.push(parentHref(pathname));
  }

  async function exitApp() {
    if (!lahkoZapustim()) return;
    // Odjava (tudi admina) -> aplikacija pokaže prijavno okno; zavihek se zapre, če ga je odprla skripta.
    if (adminSeja) await odjavaAdmina();
    await odjava();
    window.close();
  }

  return (
    <>
      <div className="flex min-h-dvh flex-col">
        {/* ============ GLAVA ============ */}
        <header className="sticky top-0 z-40 border-b-4 border-fines-500 bg-white">
          <div className="flex h-16 items-center gap-2 px-3 sm:px-4">
            {admin && (
              <IconButton hint="Odpri navigacijski meni" icon={Menu} className="lg:hidden" onClick={() => setMenuOpen(true)} />
            )}
            <Link
              href="/"
              title="Pojdi na domačo stran"
              className="flex shrink-0 items-center"
              onClick={(e) => {
                if (!lahkoZapustim()) e.preventDefault();
              }}
            >
              <Image src="/fines-logo.png" alt="FINES d.o.o. logotip" width={136} height={36} priority />
            </Link>
            {!isHome && (
              <Button
                hint="Vrni se na nadrejeno stran"
                variant="neutral"
                icon={ChevronLeft}
                className="ml-2 hidden sm:inline-flex"
                onClick={nazaj}
              >
                Nazaj
              </Button>
            )}
            <h1 className="ml-2 min-w-0 flex-1 truncate text-base font-bold text-ink-800 sm:text-lg">{title}</h1>
            {!isHome && (
              <IconButton hint="Vrni se na nadrejeno stran" variant="neutral" icon={ChevronLeft} className="sm:hidden" onClick={nazaj} />
            )}
            <IconButton
              hint={admin ? "Admin dostop je odprt - odjava admina" : "Admin dostop za urejanje navodil"}
              icon={admin ? ShieldCheck : Shield}
              variant={admin ? "primary" : "ghost"}
              onClick={odpriPrijavo}
            />
            <IconButton hint="Prikaži verzije in spremembe aplikacije" icon={Info} onClick={() => setInfoOpen(true)} />
            <span className="hidden text-xs text-ink-500 md:inline" title="Prijavljeni uporabnik">
              {adminSeja ? `${adminSeja.user.email} (admin)` : glavniAdmin ? `${email} (admin)` : email}
            </span>
            <Button hint="Odjavi se in zapri aplikacijo" variant="primary" icon={LogOut} onClick={exitApp}>
              <span className="hidden sm:inline">Izhod</span>
            </Button>
          </div>
        </header>

        <div className="flex flex-1">
          {/* ============ LEVA NAVIGACIJA (samo med admin dostopom) ============ */}
          {menuOpen && (
            <div className="fixed inset-0 z-40 bg-black/40 lg:hidden" onClick={() => setMenuOpen(false)} aria-hidden />
          )}
          {admin && (
            <aside
              className={`fixed inset-y-0 left-0 z-50 flex w-72 transform flex-col bg-ink-800 text-ink-100 transition-transform lg:sticky lg:top-16 lg:z-0 lg:h-[calc(100dvh-4rem)] lg:w-64 lg:translate-x-0 ${
                menuOpen ? "translate-x-0" : "-translate-x-full"
              }`}
            >
              <div className="flex h-16 shrink-0 items-center justify-between px-4 lg:hidden">
                <span className="font-bold text-white">Meni</span>
                <IconButton
                  hint="Zapri navigacijski meni"
                  icon={X}
                  className="text-ink-200 hover:bg-ink-700"
                  onClick={() => setMenuOpen(false)}
                />
              </div>
              <nav className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-3 py-4" aria-label="Glavna navigacija">
                <NavLink href="/" active={isHome} icon={Home} hint="Pojdi na skeniranje naloga">
                  Domov
                </NavLink>
                <div className="flex flex-col gap-2">
                  {NAV.map((group) => {
                    const aktiven = current?.group === group;
                    const prikazan = aktiven || odprtiModuli.has(group.label);
                    return (
                      <NavModul
                        key={group.label}
                        group={group}
                        aktiven={aktiven}
                        prikazan={prikazan}
                        onPreklopi={() => preklopiModul(group.label, prikazan)}
                      >
                        {group.sekcije.map((sekcija) => (
                          <NavSekcijaBlok key={sekcija.label} sekcija={sekcija} current={current?.item} pathname={pathname} />
                        ))}
                      </NavModul>
                    );
                  })}
                </div>
              </nav>
            </aside>
          )}

          {/* ============ VSEBINA ============ */}
          <main className="min-w-0 flex-1 px-3 py-4 sm:px-6 sm:py-6">{children}</main>
        </div>

        {/* ============ NOGA ============ */}
        <footer className="border-t border-ink-200 bg-white px-4 py-2 text-center text-xs text-ink-500">
          FINES d.o.o. | Work Instructions | Verzija {APP_VERSION}
        </footer>
      </div>

      <Modal open={infoOpen} title="Verzije in spremembe" onClose={() => setInfoOpen(false)}>
        <div className="flex flex-col gap-5">
          {CHANGELOG.map((v) => (
            <section key={v.verzija}>
              <div className="flex items-baseline justify-between">
                <h3 className="text-base font-bold text-fines-500">Verzija {v.verzija}</h3>
                <span className="text-xs text-ink-500">{v.datum}</span>
              </div>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink-700">
                {v.spremembe.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </Modal>
    </>
  );
}

/**
 * Modul menija (Proizvodnja, Admin ...): rahlo svetlejši blok, glava razpre / zloži vsebino.
 * Razdelki in postavke so zamaknjeni desno od imena modula.
 */
function NavModul({
  group,
  aktiven,
  prikazan,
  onPreklopi,
  children,
}: {
  group: NavGroup;
  aktiven: boolean;
  prikazan: boolean;
  onPreklopi: () => void;
  children: ReactNode;
}) {
  return (
    <div className={`rounded-xl transition-colors ${prikazan ? "bg-white/5" : "hover:bg-white/5"}`}>
      <button
        type="button"
        title={prikazan ? `Zloži modul ${group.label}` : `Razpri modul ${group.label}`}
        aria-expanded={prikazan}
        disabled={aktiven}
        onClick={onPreklopi}
        className="flex h-12 w-full items-center gap-2 rounded-xl px-3 text-left text-sm font-bold uppercase tracking-wider text-white disabled:cursor-default"
      >
        <group.icon className={`h-5 w-5 shrink-0 ${aktiven ? "text-fines-400" : "text-ink-300"}`} aria-hidden />
        <span className="flex-1">{group.label}</span>
        {!aktiven && (
          <ChevronDown className={`h-4 w-4 shrink-0 text-ink-300 transition-transform ${prikazan ? "rotate-180" : ""}`} aria-hidden />
        )}
      </button>
      {prikazan && <div className="flex flex-col gap-3 pb-3 pl-4 pr-1">{children}</div>}
    </div>
  );
}

/** Razdelek modula: oranžen naslov s tanko oranžno črto, pod njim postavke (brez razpiranja). */
function NavSekcijaBlok({ sekcija, current, pathname }: { sekcija: NavSekcija; current?: NavItem; pathname: string }) {
  return (
    <section aria-label={sekcija.label}>
      <div className="mb-1 flex items-center gap-2 px-3">
        <span className="shrink-0 text-[11px] font-bold uppercase tracking-wider text-fines-400">{sekcija.label}</span>
        <span className="h-px flex-1 bg-fines-500/40" aria-hidden />
      </div>
      <div className="flex flex-col gap-1">
        {sekcija.items.map((item) =>
          item.children ? (
            <NavPodmeni key={item.href} item={item} pathname={pathname} />
          ) : (
            <NavLink key={item.href} href={item.href} active={current === item} icon={item.icon} hint={item.hint} kmalu={item.kmalu}>
              {item.label}
            </NavLink>
          ),
        )}
      </div>
    </section>
  );
}

/** Postavka s podmenijem: klik razpre / zloži seznam podstrani. Na podstrani je razprta. */
function NavPodmeni({ item, pathname }: { item: NavItem; pathname: string }) {
  const aktivna = aktivnaPostavka(item.children ?? [], pathname);
  const [odprt, setOdprt] = useState(!!aktivna);
  const prikazan = odprt || !!aktivna;
  return (
    <div>
      <button
        type="button"
        title={item.hint}
        aria-expanded={prikazan}
        onClick={() => setOdprt(!prikazan)}
        className={`flex h-11 w-full items-center gap-3 rounded-lg px-3 text-left text-sm font-semibold transition-colors ${
          aktivna ? "text-white" : "text-ink-200 hover:bg-ink-700 hover:text-white"
        }`}
      >
        <item.icon className="h-5 w-5 shrink-0" aria-hidden />
        <span className="flex-1">{item.label}</span>
        <ChevronDown className={`h-4 w-4 shrink-0 transition-transform ${prikazan ? "rotate-180" : ""}`} aria-hidden />
      </button>
      {prikazan && (
        <ul className="ml-5 mt-1 flex flex-col gap-1 border-l border-ink-600 pl-2">
          {item.children?.map((c) => (
            <li key={c.href}>
              <NavLink href={c.href} active={aktivna === c} icon={c.icon} hint={c.hint} kmalu={c.kmalu} majhen>
                {c.label}
              </NavLink>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function NavLink({
  href,
  active,
  icon: Icon,
  hint,
  kmalu,
  majhen,
  children,
}: {
  href: string;
  active: boolean;
  icon: typeof Home;
  hint: string;
  kmalu?: boolean;
  majhen?: boolean;
  children: ReactNode;
}) {
  return (
    <Link
      href={href}
      title={hint}
      onClick={(e) => {
        if (!lahkoZapustim()) e.preventDefault();
      }}
      aria-current={active ? "page" : undefined}
      className={`flex items-center gap-3 rounded-lg px-3 text-sm font-semibold transition-colors ${majhen ? "h-10" : "h-11"} ${
        active ? "bg-fines-500 text-white" : "text-ink-200 hover:bg-ink-700 hover:text-white"
      }`}
    >
      <Icon className={`${majhen ? "h-4 w-4" : "h-5 w-5"} shrink-0`} aria-hidden />
      <span className="flex-1">{children}</span>
      {kmalu && (
        <span className="rounded-full bg-ink-600 px-2 py-0.5 text-[10px] font-bold uppercase text-ink-200">kmalu</span>
      )}
    </Link>
  );
}
