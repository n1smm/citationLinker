# Povezovalnik znanstvenega citiranja

## Kaj počne skript
Skript citationLinker.py poišče navajanja in jih poveže z referencami. Doda goto povezave in podčrtane anotacije. Izhod: output/ime_dokumenta_linked.pdf
Deluje na dokumentih tipa PDF in z načinom citiranja APA

## Zahteve
```bash
- Python 3.8–3.12 (priporočeno 3.10–3.12). testirano z 3.12.3
- requirements.txt z: pymupdf
- V isti mapi: citationLinker.py, .config, lokalni moduli v src (textScreener.py, bibliographyFinder.py, configLoad.py, inParenthesisExtractor.py).
```


### Linux (bash) namestitev skripte
1. cd v mapo s skripto
2. `python3 -m venv .venv`
   `source .venv/bin/activate`
3. `pip install --upgrade pip`
   `pip install -r requirements.txt`
4. `python3 citationLinker.py --help` - preverite če deluje

### Windows (PowerShell)
1. cd v mapo s skripto
2. `python -m venv .venv`
   `.\.venv\Scripts\Activate.ps1`
3. `pip install --upgrade pip`
   `pip install -r requirements.txt`
4. `python citationLinker.py --help` - preverite če deluje

## Konfiguracija
v mapi obstaja tudi skriti dokument .config, ki se ga lahko uredi.
za sedaj ima notri dve možnosti:
1. SPECIAL_CASE="nav. d." - to je default
    tukaj se lahko doda besede, ki zaznamujejo ponavljanje navajanja.
    Na primer če je bil prej v tekstu navedeno delo in se naslednja navajanja referirajo
    na isto delo
    lahko se dodat tudi več različnih ključnih besed, v tem primeru morajo biti zapisane na takšen način:
    SPECIAL_CASE="nav. d.", "navedeno", "navedeno delo", "nek drug neznani primer"

2. COLOR=black 
    tukaj se lahko spremeni barvo črte, ki podčrta navedbo
    možnosti: black, white, gray, blue, red

## uporaba

obstajata dve možnosti:
1. v datoteko s skripto (kjer se nahaja citationLinker.py) prenesete željene dokumente
    v tem primeru lahko uporabite samo ime dokumenta
2. če se dokumenti nahajajo kje drugje lahko vnesete celotno pot do dokumenta
    npr. (/home/uporabnik/dokumenti/dokument.pdf)

V dokumentu morate poiskati kjučno besedo ali stavek, ki zaznamuje začetek literature/spiska del
npr ("Literatura" ali "Spisek del" ali "bibliografija" ,...) - če je več besed moraj biti v ""

opcijsko lahko dodate še dodatne dve možnosti, ki sta začetek in konec teksta, kjer naj skripta išče povezave (na primer če je tekst del daljšega dokumenta) `--start-page 1 --end-page 23`


to se pravi celotna uporabja je

```bash
python3 citationLinker <ime ali pot do dokumenta> <zaznamujoca beseda> --start-page <začetna> --end-page <končna>
```
primer
```bash
python3 citationLinker "dokument.pdf" "Litaratura" --start-page 2 --end-page 24
```
ali samo 
```bash
python3 citationLinker "/home/user/Documents/dokument.pdf" "Spisek del" 
```

na operacijskih sistemih windows je vse podobno razlika le v uporabi python namesto python3
```windows
python citationLinker "dokument.pdf" "Litaratura" --start-page 2 --end-page 24
```

ne pozabite, da morate pred vsako ponovno uporabo najprej zagnati pythonovo virtualno okolje, kot v koraku namestitve:
```bash
source .venv/bin/activate
```
ali windows:
```windows
.\.venv\Scripts\Activate.ps1
```


## zmogljivosti in omejitve skripte

Trenutno skripta deluje samo za posamezne članke oz. dokumente ki imajo vire literature samo na enem mestu (npr. na koncu teksta). 
Ravno tako je omejeno na citiranje stila APA.


### primeri navajanja, ki jih skripta prepozna:

(Deckard idr. 2015: 17–22, 49–56).
(Trocki 2008)
(Trocki 2008: 7–8; Davidson 2019a: 24–28).
(Nav. po Davidson 2019b: 180)
(prim. Zima 2015: 2–4).
Peter V. Zima (2015: xi, 2–3, passim)
(Adorno 1966: 353–354)
(Pascale Casa-nova [2004] //navajanje ko je oklepaj v oklepaju 
Gačev (1964)
Moretti (2011: 13–20, 36–37)
(Trocki 2008:7–8; Davidson 2019a:24–28)
(Kermauner 1970: 93; 2013: 219)
(prim. Kermauner 1968a: 12; 1970: 6–7; 1971: 140–141, 171–172, 221–222; Svetina 2013: 510–545).
(nav. d.: 17–22, 49–56).

### opombe:

ko je navajanih več del hkrati morajo biti ta razdeljena z ;
če je navajanje v oklepajih (tekst ... priimek [leto] ... ) mora biti priimek takoj pred letom,
to se pravi nebi delovalo (tekst ... priimek idr. [leto] ...)
Če priimek ni zapisan z veliko začetnico, ga skript ne bo prepoznal
Če se navedeno leto ali priimek razlikuje od tega kako je zapisano v litaraturi ga skrip ne bo prepoznal


### literatura

Pomembno je da je vsako novo delo v litaraturi zabeleženo na približno takšen način:

Adorno, Theodor W., 1969: Prismen: Kulturkritik und Gesellschaft. Berlin:
Suhrkamp Verlag.

To se pravi je pomembo da po letu sledi dvopičje (:), in da si sledijo priimek, ime, leto

