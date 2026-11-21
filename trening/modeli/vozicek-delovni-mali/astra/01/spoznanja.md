# Predlogi za skupno znanje

- [CAD uvoz] Pri tem sestavu 28 definicij MANIFOLD_SOLID_BREP, 28 pojavitev izdelkov in 92 postavljenih teles opisuje tri različna štetja. Vsako od štirih koles združuje 17 teles. Korenski pregled in seštevek po pojavih sta oba dala 92.
- [Identifikacija delov] V tem izvozu je ime PRODUCT šifra, opis izdelka pa je v tretjem besedilnem polju. Združitev fizičnih vrstic in dekodiranje STEP X2 sta obnovila opisa »Plošča kolesa« in »Nosilec ročaja«.
- [Mreža] Uspešno zaključen BRepMesh ne zagotavlja mreže vsake ploskve. Dve ploskvi kolesa po prvem prehodu nista imeli trikotnikov. Tesseliranje posamezne kopije ploskve z manjšim odstopanjem je uspelo pri obeh.
- [Montaža] Pri P117 bi samo pregled slike spregledal presek s štirimi povezavami. Presek B-Rep v končni legi je znašal približno 2,64–5,31 mm³ na povezavo, pri odmiku 0,5 mm pa nič.
- [Animacija] Enako definirana premika je bilo mogoče zapisati kot ločeni animaciji glTF in uporabiti za video. Ponovno branje glTF je preverilo ciljni ID, odmik in končno lego obeh delov.
- [Igrišče] Predlog za model.json je polje za dovoljene konstrukcijske tolerance in revizijo. Ta poskus lahko izmeri stik P117 s povezavami, podatek za presojo sprejemljivosti pa manjka.
