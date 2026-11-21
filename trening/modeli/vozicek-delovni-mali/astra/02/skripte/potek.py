from osnova import OUT,EXPORT,read,save
import numpy as np

FPS=25
WHEELS=["P122","P123","P124","P125"]
BOARDS=["P118","P121","P117"]
GROUP_NAMES=dict(kolesa="Kolesa",nosilci="Vmesni povezavi",rocaj="Ročaj",spodnja="Spodnja polica",srednja="Srednja polica",zgornja="Zgornja polica")

def sequence(parts,fix):
    def ids(lo,hi):
        return [f"P{i:03d}" for i in range(lo,hi+1)]
    def group(g):
        return [x["id"] for x in fix if x["skupina"]==g]
    def step(key,title,body,pids,refs,seconds,warning,mode,tag,delta=None):
        return dict(st=len(rows)+1,kljuc=key,naslov=title,opis=body,deli=pids,referencni_deli=refs,
                    prikaz=tag,gibanje=dict(tip=mode,trajanje_s=seconds,od_mm=delta or [0,0,0],do_mm=[0,0,0]),
                    kamera=dict(pogled={"var":"izometrija in detajl stika","kolo":"štirje lokalni pogledi","vijak":"detajl in pregled mest","polica":"izometrija zgoraj"}.get(mode,"lokalni pogled")),
                    opozorila=[warning],potrditev="ni znano / zahteva potrditev")
    rows=[]
    rows.append(step("okvir","Stiki ogrodja","Poravnaj stebre s spodnjim okvirom. Označeni stiki so kandidati za varjenje.",ids(101,116),[],5,"Vrsto in dolžino zvara določi varilni načrt.","var","PREDLOG SPOJA"))
    rows.append(step("stiki","Kje se deli stikajo","Sled pokaže rob, ki ga delita dve CAD-telesi. Prikazani so štirje značilni stiki ogrodja.",["P101","P104","P113","P108","P110","P112"],[],6,"Prikazani robovi so kandidati za varjenje. Obseg, stran in zaporedje varjenja zahtevajo varilno risbo.","var","STIK IZ CAD · ZVAR JE PREDLOG"))
    rows.append(step("poravnava","Poravnava štirih koles","Prirobnico vsakega kolesa približaj spodnji strani njegove plošče.",WHEELS,ids(113,116),5,"Lega je iz CAD. Podpiranje vozička zahteva potrditev.","kolo","LEGA IZ STEP",[0,0,-38]))
    rows.append(step("kolesa","Vijačenje koles","Za vsako kolo so prikazani štirje vijaki. Konice se ustavijo na stiku z nosilno ploščo.",group("kolesa"),WHEELS+ids(113,116),7,"Na vseh 16 oseh je plošča v modelu polna. Izvedbo izvrtin, navojev ali matic mora potrditi konstruktor.","vijak","16 MEST · VIJAKI SO PREDLOG"))
    rows.append(step("prerez","Zakaj se vijak ustavi","Prirobnica ima režo. Na isti osi jo zapira 3 mm debela jeklena plošča okvirja. Enako velja za vsa štiri kolesa.",["P123","P113"],group("kolesa"),5,"Pred montažo preveri dejansko ploščo in risbo pritrditve. V navodilu manjkajoče izvrtine niso dodane.","prerez","PREGLED SPOJA"))
    rows.append(step("zvar_rocaja","Zvarjenec ročaja","Cev se konča na nosilcih. Sled na obeh koncih prikazuje možni potek zvara.",ids(98,100),[],5,"STEP opisuje ročaj kot zvarjenec. Potek in velikost zvara zahtevata varilno risbo.","var","ZVARJENEC IZ STEP"))
    rows.append(step("rocaj","Pritrditev ročaja","Vsak nosilec ima dve odprtini. Štirje vijaki so poravnani z odprtinami v stebrih.",group("rocaj"),["P098","P100","P107","P108"],6,"Šesterokotna odprtina dopušča navojni vložek. Njegova izvedba in vijak zahtevata kosovnico.","vijak","4 MESTA · PREDLOG IZVEDBE"))
    rows.append(step("nosilci","Vmesni povezavi","Na vsakem koncu povezave se podolgovata odprtina ujema z odprtino stebra.",group("nosilci"),["P119","P120"]+ids(105,108),6,"Izvedbo nasprotnega navoja ali vložka potrdi s kosovnico.","vijak","4 MESTA · PREDLOG IZVEDBE"))
    rows.append(step("spodnja","Spodnja polica","Šest manjših izvrtin gleda proti spodnji polici. Večje odprtine na spodnji steni cevi omogočajo dostop.",group("spodnja"),["P118","P101","P102"],6,"Vijaki in njihova dolžina so shematski. Izbor mest zahteva potrditev.","vijak","6 MEST · PREDLOG IZVEDBE"))
    rows.append(step("srednja","Srednja polica","Na povezavah je šest spodnjih in deset bočnih izvrtin, usmerjenih v iveral.",group("srednja"),["P121","P119","P120"],6,"Končni izbor spodnjih in bočnih mest mora potrditi tehnolog.","vijak","16 MEST · PREDLOG IZVEDBE"))
    rows.append(step("polaganje","Lega zgornje police","Daljši rob police poravnaj z daljšo stranico okvirja. Prikaz se konča v legi STEP.",["P117"],ids(109,112),5,"CAD v končni legi pokaže majhna prekrivanja na štirih zgornjih povezavah.","polica","LEGA IZ STEP",[0,0,110]))
    rows.append(step("zgornja","Zgornja polica","Osem spodnjih in osemnajst bočnih izvrtin je usmerjenih proti polici. Prikazane so vse možne pritrdilne točke.",group("zgornja"),["P117"]+ids(109,112),7,"Izbiro mest in dolžino vijaka je treba preveriti na risbi ali prototipu.","vijak","26 MEST · PREDLOG IZVEDBE"))
    return rows


def motion(p):
    u=np.clip((p-.17)/.64,0.,1.)
    return u*u*(3.-2.*u)

def axis_matrix(axis):
    z=np.array(axis,dtype=float)
    x=np.array([1.,0,0]) if abs(z[0])<.9 else np.array([0.,1,0])
    return np.column_stack((x,np.cross(z,x),z))

def states(step,p,sites):
    u=motion(p)
    data={}
    for pid in step["deli"]:
        if pid in sites:
            site=sites[pid]
            travel={"kolesa":22,"spodnja":46}.get(site["skupina"],15)
            shift=-np.array(site["os"])*(1-u)*travel
            data[pid]=(shift,2*np.pi*1.75*u)
        elif step["gibanje"]["tip"] in ("kolo","polica"):
            data[pid]=(np.array(step["gibanje"]["od_mm"])*(1-u),0.)
    return data

