# Spoznanja – Fable, vozicek-delovni-mali, poskus 02

Dopolnjuje spoznanja iz fable/01 (ta še veljajo; tukaj jih ne ponavljam).

- [Montaža] Način spajanja se da v veliki meri **razbrati iz geometrije STEP**, če se analizirajo luknje in stiki, ne samo položaji delov. Na tem modelu: 52 spojev, od tega 34 varjenih, 10 vijačnih, 8 „polica + vijaki". Preverjeno v fable/02 (`spoji.json`, vsak spoj ima zapisan dokaz).
- [Montaža] Luknje je treba brati kot **notranje zanke na ravnih ploskvah**, ne kot valjaste ploskve. Tako se zajamejo tudi šestkotne luknje in utori, ki nosijo največ informacije. Preverjeno v fable/02.
- [Montaža] Predlog pravila: **šestkotna luknja z zevom 9,1 mm v tankostenski cevi = šestkotna zakovična matica M6** (standardni izrez 9,0; M5 → 7,0; M8 → 11,0). Na tem modelu to potrjuje soosna prehodna luknja 6,4–6,5 mm in reža 0,5 mm med deloma (prirobnica matice). Domneva, zahteva potrditev človeka.
- [Montaža] Predlog pravila: **par soosnih lukenj v istem profilu, večja (Ø12) v eni steni in manjša (Ø4,5) v nasprotni = dostopna + prehodna luknja**; vijak se vstavi skozi profil. Preverjeno geometrijsko v fable/02 (spodnja polica), način pritrditve je domneva.
- [Montaža] Predlog pravila: **stik jeklo–jeklo z ravno stično ploskvijo in brez soosnih lukenj = varjenje**. Ujema se s pripombo človeka (cevi, okvirji, pločevina se varijo). Obod stične ploskve je uporaben kot mesto zvara; vrste in mere zvara ne pove.
- [Montaža] Kupljeni deli imajo lahko pritrdilne luknje, **nasprotni del pa ne** (kolo ima 4 utore 9,2x10,7 → M8, plošča kolesa je brez lukenj). Zaznava mora zato upoštevati tudi „luknja + poln material za njo", ne samo pare lukenj.
- [Montaža] Prag bližine delov pri iskanju spojev mora biti vsaj ~2 mm: v CAD je med vijačenimi deli reža (0,5–1,4 mm na tem modelu), stika ni. S pragom 0,6 mm sta nosilca ročaja izpadla. Preverjeno v fable/02.
- [Montaža] V modelu je veliko **lukenj brez para** (80 prostih šestkotnih v nogah, 28 lukenj Ø4, 10 šestkotnih z zevom 7,1). Zaznava jih mora izpisati posebej in jih ne sme siliti v spoje. Njihov namen je neznan.
- [Montaža] Ko je okvir zvarjen pred končno montažo, se spremenijo dovoljene poti: vmesna polica ne more več od zgoraj (16 trkov z zgornjimi povezavami), lahko pa s sprednje strani, če je sprednja vmesna povezava nameščena za njo. Preverjeno z detektorjem trkov v fable/02.
- [Identifikacija delov] Razred materiala za prikaz se da oceniti **brez imena materiala**: poln kvader debeline 8–45 mm brez lukenj → les / plošča; ekvivalentna debelina stene 2·V/A ≤ 4 mm → jeklena pločevina ali cev; več teles v enem produktu → kupljen sestavni del. Z imenom v STEP se ujema pri 11 od 12 produktov. Inoxa od jekla geometrija ne loči. Razvito na enem modelu – preveriti na drugem.
- [Identifikacija delov] Pri iskanju ključnih besed v razredih paziti na podnize („več teles" vsebuje „les"). Napaka je v fable/02 kolo razvrstila kot les.
- [Render / video] VTK zmore precej več od osnovnega senčenja: PBR materiali (`SetInterpolationToPBR`), okoljska osvetlitev iz proceduralne slike, SSAO (`UseSSAOOn`), teksture, robovi (`vtkFeatureEdges`). 3891 sličic 2880x1620 → 1080p v 8 min 40 s na Intel UHD 770. Preverjeno v fable/02.
- [Render / video] Velika talna ravnina skupaj s SSAO da vodoravne pasove. Boljša je mehka senca (prosojna tekstura) pod izdelkom. Preverjeno v fable/02.
- [Render / video] Napis ob delu naj nosi **ime in količino** („4x Kolo fi80 …") z vodilno črto do vsakega kosa; ID in šifra drobno. Za spoj je potreben detajlni pogled (kamera se približa enemu spoju, vsi enaki spoji se animirajo hkrati), ker so zvari in vijaki v pogledu celega izdelka premajhni.
- [Render / video] Način zagona „samo kontrolne sličice" (`--slicice`, ~40 s namesto 9 min) omogoča več krogov popravkov pred končnim renderjem.
- [Orodja] Tudi `pip install bpy` (Blender kot Python modul, bpy 5.3.0 obstaja za Python 3.13) je varnostni klasifikator Claude Code zavrnil, enako kot prenos zip. Blender mora namestiti človek ali dodati dovoljenje.
- [Orodja] Pri urejanju Python skript iz Git Bash heredoca se `\n` v nizih in šumniki lahko pokvarijo; zanesljivejše je urejanje datoteke neposredno.
- [Igrišče] Predlog: v `ZNANJE.md` dodati razdelek „Standardi spajanja" (kolesa se vijačijo; cevi in pločevina se varijo; mere izrezov za zakovične matice; kateri vijak za lesene police), da pravil ni treba vsakič sklepati.
- [Igrišče] Predlog: v `model.json` dodati polja `povrsinska_zascita` (barvano / surovo / cinkano) in `dekor_polic`, ker iz STEP ni razvidno (police imajo material „Iveral" in skoraj črno barvo, ime pa „lesena").
- [Igrišče] Predlog: aplikacija naj prikaže tudi `spoji.json` (tabela spojev z dokazom), ker je to glavni podatek, ki ga mora tehnolog potrditi.
