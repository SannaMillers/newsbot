#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Newsbot - sammelt auf Knopfdruck die Schlagzeilen des Tages zu KI, RPA,
Automatisierung, Rechenzentren, Investitionen und Big Tech und legt sie
als Lesedatei im Ordner "news" ab.

Nur Python-Standardbibliothek. Start: 4_newsbot.bat oder python newsbot.py
Quellen stehen in quellen.txt und koennen dort frei geaendert werden.
"""

import datetime
import html
import os
import queue
import re
import threading
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

# Die Oberflaeche ist optional: auf einem Server ohne Bildschirm laeuft
# dieselbe Datei mit "python newsbot.py --cli" ganz ohne tkinter.
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext
    OBERFLAECHE = True
except ImportError:  # pragma: no cover
    OBERFLAECHE = False
    tk = ttk = messagebox = scrolledtext = None

ORDNER = os.path.dirname(os.path.abspath(__file__))
QUELLDATEI = os.path.join(ORDNER, "quellen.txt")
AUSGABE = os.path.join(ORDNER, "news")
TITEL = "Nachrichtenlage"
OHNE_FILTER = False   # True = alle frischen Meldungen behalten, ohne Themenfilter

MAX_JE_QUELLE = 30         # Startwert, im Fenster einstellbar
STUNDEN_ZURUECK = 36       # Startwert, im Fenster einstellbar
ZEITLIMIT = 25             # Sekunden je Quelle

# Themen und ihre Suchmuster. Zahl = Gewicht.
# Die Muster sind regulaere Ausdruecke:
#   \b...    Wortanfang, passt auch auf Komposita (automatisier -> Automatisierung)
#   \b...\b  ganzes Wort, verhindert Zufallstreffer (chip faengt sonst chiptunes)
# Neue Begriffe einfach in die passende Liste eintragen.
THEMEN = {
    "KI": (3, [r"\bki\b", r"\bki-", r"künstliche intelligenz", r"artificial intelligence",
               r"\bai\b", r"\bai-", r"\bllm", r"sprachmodell", r"language model",
               r"openai", r"anthropic", r"\bclaude\b", r"\bgpt", r"\bgemini\b",
               r"copilot", r"mistral", r"deepseek", r"inferenz", r"inference",
               r"\bagent", r"machine learning", r"neuronal", r"\bneural",
               r"prompt", r"chatbot", r"generativ"]),
    "RPA / Automatisierung": (3, [r"\brpa\b", r"robotic process", r"uipath",
                                  r"automatisier", r"\bautomation", r"workflow",
                                  r"orchestrator", r"orchestrier", r"prozessautomat",
                                  r"low-?code", r"no-?code", r"\bbot\b", r"\bbots\b",
                                  r"\brobot", r"\broboter"]),
    "Rechenzentren": (3, [r"rechenzentr", r"data cent", r"datacenter", r"hyperscal",
                          r"colocation", r"kühlung", r"\bcooling\b", r"gigawatt",
                          r"megawatt", r"stromverbrauch", r"power usage",
                          r"\bnvidia\b", r"\bgpus?\b", r"\bchips?\b", r"halbleiter",
                          r"semiconductor", r"\btpu\b", r"serverfarm"]),
    "Investitionen": (2, [r"milliarde", r"\bbillion\b", r"\bmillion", r"\bfunding\b",
                          r"finanzierungsrunde", r"investit", r"\binvestment",
                          r"\bipo\b", r"börsengang", r"übernahme", r"acquisition",
                          r"acquires", r"\braises\b", r"valuation", r"bewertung",
                          r"\bumsatz", r"quartalszahlen", r"\bearnings\b",
                          r"\betf\b", r"\bnasdaq\b", r"\baktie"]),
    "Big Tech": (2, [r"microsoft", r"\bgoogle\b", r"alphabet", r"\bamazon\b", r"\baws\b",
                     r"\bmeta\b", r"\bapple\b", r"\btesla\b", r"\boracle\b", r"\bibm\b",
                     r"\bsap\b", r"salesforce", r"broadcom", r"\bintel\b", r"\bamd\b",
                     r"\btsmc\b", r"palantir", r"\bxai\b", r"servicenow"]),
    "KI-Politik und Regulierung": (3, [
        r"\bai act\b", r"ki-verordnung", r"ki-gesetz", r"ai-gesetz",
        r"europäisch\w* parlament", r"european parliament", r"europaparlament",
        r"\bmep\b", r"abgeordnete", r"eu-kommission", r"europäische kommission",
        r"european commission", r"\bbrüssel\b", r"\bbrussels\b", r"\btrilog",
        r"\brat der eu\b", r"ministerrat", r"\bgpai\b", r"\bdsa\b", r"\bdma\b",
        r"digital services act", r"digital markets act", r"data act",
        r"\bgesetzentwurf", r"\bverordnung", r"\brichtlinie\b", r"\bnovelle\b",
        r"regulierung", r"\bregulation\b", r"\bregulat", r"\baufsicht",
        r"bundesnetzagentur", r"\bkartellamt", r"antitrust", r"wettbewerbshüter",
        r"\bmoratorium\b", r"guardrails", r"\bcompliance\b", r"gesetzespaket",
        r"\bbundestag\b", r"\bbundesrat\b", r"executive order", r"\bkongress\b",
        r"\bcongress\b", r"\bsenat", r"lobbying", r"\bethikrat\b",
        r"grundrecht", r"haftung", r"transparenzpflicht", r"kennzeichnungspflicht"]),
    "Krypto": (2, [r"\bbitcoin\b", r"\bbtc\b", r"krypto", r"\bcrypto", r"ethereum",
                   r"stablecoin", r"\bmining\b", r"\bwallet\b", r"blockchain",
                   r"\biren\b"]),
    "Energie und Gebäude": (2, [r"wärmepumpe", r"wärmenetz", r"nahwärme", r"fernwärme",
                                r"energieberat", r"\bgeg\b", r"energieausweis",
                                r"\bbafa\b", r"\bbeg\b", r"förderprogramm",
                                r"sanierung", r"photovoltaik", r"\bpv-anlage",
                                r"solar", r"strompreis", r"netzentgelt",
                                r"stromnetz", r"\bheizung"]),
    "Prozesse und ERP": (2, [r"\berp\b", r"\babas\b", r"\bsap\b", r"kundenservice",
                             r"customer service", r"ticketsystem", r"servicedesk",
                             r"prozessmanagement", r"business process",
                             r"digitalisierung", r"schnittstelle", r"\bapi\b"]),
    "Sicherheit": (1, [r"sicherheitslücke", r"schwachstelle", r"\bcve-", r"ransomware",
                       r"datenleck", r"\bdata breach\b", r"cyberangriff",
                       r"cyberattack", r"\bphishing\b", r"\bdsgvo\b", r"datenschutz"]),
}


# Zweiter Themensatz: nur Rechtsetzung. Wird mit "--themen recht" aktiv und
# haelt aus den Nachrichtenquellen das heraus, was wirklich Gesetz, Verordnung
# oder Foerderregel ist - statt alles durchzulassen.
RECHT = {
    "Gesetzgebung Bund": (3, [
        r"\bgesetz", r"\bbundestag\b", r"\bbundesrat\b", r"\bkabinett\b",
        r"referentenentwurf", r"regierungsentwurf", r"\bnovelle\b",
        r"\bverordnung", r"\brichtlinie\b", r"bundesgesetzblatt",
        r"\bdrucksache", r"\blesung\b", r"\bvermittlungsausschuss\b",
        r"tritt in kraft", r"\bin kraft\b", r"beschlossen", r"verabschiedet",
        r"zugestimmt", r"\breform\b", r"\bgesetzespaket\b",
        r"\bbundesverfassungsgericht\b", r"\bbgh\b", r"\bbfh\b",
        r"\bbverwg\b", r"\bbag\b", r"\burteil\b", r"\brechtsprechung\b"]),
    "EU-Recht": (3, [
        r"eu-verordnung", r"eu-richtlinie", r"\bai act\b", r"digital services act",
        r"digital markets act", r"data act", r"\bdsgvo\b",
        r"europäisch\w* parlament", r"europaparlament", r"eu-kommission",
        r"europäische kommission", r"\bbrüssel\b", r"\btrilog", r"\bmitgliedstaat",
        r"amtsblatt", r"\bcelex", r"european commission", r"european parliament",
        r"\bdirective\b", r"\bregulation\b", r"enters into force"]),
    "Pflichten und Fristen": (2, [
        r"meldepflicht", r"nachweispflicht", r"dokumentationspflicht",
        r"kennzeichnungspflicht", r"transparenzpflicht", r"\bfrist\b",
        r"\bstichtag\b", r"\bübergangsfrist\b", r"\bbussgeld", r"\bstrafe\b",
        r"\bsanktion", r"\bhaftung", r"\bcompliance\b", r"\baufsicht"]),
    "Steuern und Abgaben": (2, [
        r"\bsteuer", r"\babgabe", r"\bumlage\b", r"\bbeitragssatz\b",
        r"\bmindestlohn\b", r"\bsozialversicherung", r"\brente", r"\bkindergeld\b",
        r"\bwohngeld\b", r"\bbürgergeld\b", r"\bgrundsicherung\b",
        r"\bfreibetrag\b", r"\bpauschale\b"]),
    "Foerderung": (2, [
        r"\bförder", r"\bzuschuss", r"\bbafa\b", r"\bkfw\b", r"\bbeg\b",
        r"\bgeg\b", r"\beeg\b", r"\bbew\b", r"antragsfrist", r"richtlinie"]),
    "Arbeit und Unternehmen": (2, [
        r"arbeitsrecht", r"arbeitszeit", r"\btarif", r"\bbetriebsrat\b",
        r"lieferkettengesetz", r"\bwhistleblow", r"hinweisgeberschutz",
        r"\bvergaberecht\b", r"\bhandelsregister\b", r"\bgwg\b"]),
}

BG       = "#11131a"
BG_KARTE = "#191c26"
BG_FELD  = "#0d0f15"
FG       = "#e8e9ee"
FG_MATT  = "#8b90a3"
AKZENT   = "#4a7dff"
AKZENT_D = "#3563e0"
LINIE    = "#262a38"


# ---------------------------------------------------------------------------
# Quellen und Abruf
# ---------------------------------------------------------------------------
def quellen_lesen():
    if not os.path.exists(QUELLDATEI):
        raise FileNotFoundError("quellen.txt fehlt im Ordner " + ORDNER)
    quellen = []
    with open(QUELLDATEI, "r", encoding="utf-8") as datei:
        for zeile in datei:
            zeile = zeile.strip()
            if not zeile or zeile.startswith("#"):
                continue
            teile = [t.strip() for t in zeile.split("|")]
            if len(teile) < 3:
                continue
            quellen.append({"name": teile[0], "kategorie": teile[1], "url": teile[2]})
    return quellen


def text_saeubern(roh):
    if not roh:
        return ""
    ohne_tags = re.sub(r"<[^>]+>", " ", roh)
    entschluesselt = html.unescape(ohne_tags)
    return re.sub(r"\s+", " ", entschluesselt).strip()


def datum_lesen(wert):
    if not wert:
        return None
    wert = wert.strip()
    formate = [
        "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y",
    ]
    bereinigt = wert.replace("GMT", "+0000").replace("UTC", "+0000")
    bereinigt = re.sub(r"(\+\d{2}):(\d{2})$", r"\1\2", bereinigt)
    for form in formate:
        try:
            zeit = datetime.datetime.strptime(bereinigt, form)
            if zeit.tzinfo:
                zeit = zeit.astimezone().replace(tzinfo=None)
            return zeit
        except ValueError:
            continue
    return None


def feed_holen(url):
    anfrage = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) newsbot/1.0",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    })
    with urllib.request.urlopen(anfrage, timeout=ZEITLIMIT) as antwort:
        return antwort.read()


# Amtliche Feeds (Bundesgesetzblatt) lassen die Beschreibung leer und legen
# den Kontext in eigene Felder. Die werden hier zur Beschreibung zusammen-
# gesetzt, damit im Digest mehr steht als der nackte Gesetzestitel.
ZUSATZFELDER = {
    "typ": "Typ",
    "initiant": "Initiant",
    "fundstelle": "Fundstelle",
    "sachgebiet": "Sachgebiet",
    "amtliche-abkuerzung": "Abkuerzung",
    "shorttitle": "Kurztitel",
}


def feed_auswerten(rohdaten, quelle, hoechstzahl=None):
    # Manche Server liefern eine HTML-Fehlerseite mit Status 200 oder stellen
    # dem XML Leerzeichen voran - beides laesst den Parser sonst scheitern.
    if isinstance(rohdaten, bytes):
        rohdaten = rohdaten.lstrip()
        schnipsel = rohdaten[:200].lower()
        if schnipsel.startswith(b"<!doctype html") or schnipsel.startswith(b"<html"):
            raise ValueError("HTML statt RSS erhalten")
    hoechstzahl = hoechstzahl or MAX_JE_QUELLE
    wurzel = ET.fromstring(rohdaten)
    eintraege = []

    # RSS 2.0
    for element in wurzel.iter():
        if element.tag.lower().endswith("item"):
            titel = beschreibung = link = datum = ""
            zusatz = []
            for kind in element:
                name = kind.tag.lower().split("}")[-1]
                if name == "title":
                    titel = text_saeubern(kind.text)
                elif name in ("description", "summary", "encoded"):
                    if not beschreibung:
                        beschreibung = text_saeubern(kind.text)
                elif name == "link":
                    link = (kind.text or "").strip()
                elif name in ("pubdate", "date", "published", "updated"):
                    if not datum:
                        datum = kind.text or ""
                elif name in ZUSATZFELDER:
                    # amtliche Feeds wie das Bundesgesetzblatt liefern den
                    # Kontext in eigenen Feldern statt in der Beschreibung
                    wert = text_saeubern(kind.text)
                    if wert:
                        zusatz.append("{}: {}".format(ZUSATZFELDER[name], wert))
            if zusatz:
                beschreibung = (beschreibung + "  " if beschreibung else "") + \
                    " | ".join(zusatz)
            if titel:
                eintraege.append({"titel": titel, "text": beschreibung,
                                  "link": link, "zeit": datum_lesen(datum),
                                  "quelle": quelle["name"],
                                  "kategorie": quelle["kategorie"]})

    # Atom
    if not eintraege:
        for element in wurzel.iter():
            if element.tag.lower().endswith("entry"):
                titel = beschreibung = link = datum = ""
                for kind in element:
                    name = kind.tag.lower().split("}")[-1]
                    if name == "title":
                        titel = text_saeubern(kind.text)
                    elif name in ("summary", "content"):
                        if not beschreibung:
                            beschreibung = text_saeubern(kind.text)
                    elif name == "link":
                        link = kind.attrib.get("href", link)
                    elif name in ("published", "updated"):
                        if not datum:
                            datum = kind.text or ""
                if titel:
                    eintraege.append({"titel": titel, "text": beschreibung,
                                      "link": link, "zeit": datum_lesen(datum),
                                      "quelle": quelle["name"],
                                      "kategorie": quelle["kategorie"]})
    return eintraege[:hoechstzahl]


def muster_bauen(themen):
    return {thema: (gewicht, re.compile("|".join(begriffe), re.IGNORECASE))
            for thema, (gewicht, begriffe) in themen.items()}


_MUSTER = muster_bauen(THEMEN)


def bewerten(eintrag):
    """Punkte nach Themen. Der Titel zaehlt doppelt, damit Randnotizen aus dem
    Beschreibungstext keine Meldung nach oben spuelen."""
    titel = eintrag["titel"]
    rumpf = eintrag["text"][:400]
    punkte = 0
    treffer = []
    for thema, (gewicht, muster) in _MUSTER.items():
        im_titel = bool(muster.search(titel))
        im_text = bool(muster.search(rumpf))
        if im_titel or im_text:
            punkte += gewicht * (2 if im_titel else 1)
            treffer.append((gewicht * (2 if im_titel else 1), thema))
    eintrag["punkte"] = punkte
    eintrag["themen"] = [t for _, t in sorted(treffer, reverse=True)]
    return punkte


def digest_schreiben(eintraege, fehler, anzahl_quellen, stunden=STUNDEN_ZURUECK):
    os.makedirs(AUSGABE, exist_ok=True)
    jetzt = datetime.datetime.now()
    pfad = os.path.join(AUSGABE, "news_{}.md".format(jetzt.strftime("%Y-%m-%d_%H%M")))

    nach_thema = {}
    for eintrag in eintraege:
        schluessel = eintrag["themen"][0] if eintrag["themen"] else "Sonstiges"
        nach_thema.setdefault(schluessel, []).append(eintrag)

    zeilen = []
    zeilen.append("# {} {}".format(TITEL, jetzt.strftime("%d.%m.%Y %H:%M")))
    zeilen.append("")
    zeilen.append("{} Meldungen aus {} Quellen, Zeitraum der letzten {} Stunden."
                  .format(len(eintraege), anzahl_quellen, stunden))
    zeilen.append("")
    zeilen.append("---")
    zeilen.append("")

    for thema in sorted(nach_thema, key=lambda t: -len(nach_thema[t])):
        zeilen.append("## {}".format(thema))
        zeilen.append("")
        for eintrag in nach_thema[thema]:
            zeit = eintrag["zeit"].strftime("%d.%m. %H:%M") if eintrag["zeit"] else "ohne Datum"
            zeilen.append("### {}".format(eintrag["titel"]))
            zeilen.append("*{} - {}*".format(eintrag["quelle"], zeit))
            zeilen.append("")
            if eintrag["text"]:
                zeilen.append(eintrag["text"][:600])
                zeilen.append("")
            if eintrag["link"]:
                zeilen.append(eintrag["link"])
                zeilen.append("")
        zeilen.append("")

    if fehler:
        zeilen.append("---")
        zeilen.append("")
        zeilen.append("## Quellen ohne Antwort")
        zeilen.append("")
        for name, grund in fehler:
            zeilen.append("- {}: {}".format(name, grund))
        zeilen.append("")

    inhalt = "\n".join(zeilen)
    with open(pfad, "w", encoding="utf-8") as datei:
        datei.write(inhalt)
    with open(os.path.join(AUSGABE, "latest.md"), "w", encoding="utf-8") as datei:
        datei.write(inhalt)
    return pfad


# ---------------------------------------------------------------------------
# Sammellauf - wird von der Oberflaeche und von der Kommandozeile benutzt
# ---------------------------------------------------------------------------
def sammeln(je_quelle=MAX_JE_QUELLE, stunden=STUNDEN_ZURUECK, melden=print,
            fortschritt=None):
    """Fragt alle Quellen ab und schreibt den Digest. Gibt (Pfad, Anzahl) zurueck."""
    quellen = quellen_lesen()
    melden("{} Quellen, bis zu {} Meldungen je Quelle, Zeitraum {} Stunden\n"
           .format(len(quellen), je_quelle, stunden))
    melden("  {:<22} {:>7} {:>7} {:>8}".format("Quelle", "gesamt", "frisch", "passend"))

    alle, fehlerliste = [], []
    grenze = datetime.datetime.now() - datetime.timedelta(hours=stunden)

    for nummer, quelle in enumerate(quellen, start=1):
        if fortschritt:
            fortschritt(nummer, len(quellen), quelle["name"])
        try:
            eintraege = feed_auswerten(feed_holen(quelle["url"]), quelle, je_quelle)
            frisch = [e for e in eintraege if e["zeit"] is None or e["zeit"] >= grenze]
            for eintrag in frisch:
                bewerten(eintrag)
            passend = frisch if OHNE_FILTER else [e for e in frisch if e["punkte"] > 0]
            alle.extend(passend)
            melden("  {:<22} {:>7} {:>7} {:>8}".format(
                quelle["name"][:22], len(eintraege), len(frisch), len(passend)))
        except urllib.error.HTTPError as fehler:
            fehlerliste.append((quelle["name"], "HTTP {}".format(fehler.code)))
            melden("  {:<22} keine Antwort (HTTP {})".format(
                quelle["name"][:22], fehler.code))
        except Exception as fehler:  # noqa: BLE001
            fehlerliste.append((quelle["name"], type(fehler).__name__))
            melden("  {:<22} keine Antwort ({})".format(
                quelle["name"][:22], type(fehler).__name__))

    gesehen, eindeutig = set(), []
    for eintrag in sorted(alle, key=lambda e: (-e["punkte"],
                                               -(e["zeit"] or grenze).timestamp())):
        schluessel = re.sub(r"[^a-z0-9]", "", eintrag["titel"].lower())[:45]
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        eindeutig.append(eintrag)

    if not eindeutig:
        melden("\nKeine passenden Meldungen gefunden.")
        return None, 0

    pfad = digest_schreiben(eindeutig, fehlerliste, len(quellen), stunden)
    return pfad, len(eindeutig)


# ---------------------------------------------------------------------------
# Oberflaeche
# ---------------------------------------------------------------------------
class Newsbot(tk.Tk if OBERFLAECHE else object):
    def __init__(self):
        super().__init__()
        self.title("Newsbot")
        self.configure(bg=BG)
        self.geometry("900x680")
        self.minsize(780, 560)
        self.nachrichten = queue.Queue()
        self._stil()
        self._aufbau()
        self.after(120, self._queue_pruefen)

    def _stil(self):
        stil = ttk.Style(self)
        try:
            stil.theme_use("clam")
        except tk.TclError:
            pass
        stil.configure("TFrame", background=BG)
        stil.configure("TLabel", background=BG_KARTE, foreground=FG, font=("Segoe UI", 10))
        stil.configure("Kopf.TLabel", background=BG, foreground=FG,
                       font=("Segoe UI Semibold", 20))
        stil.configure("Unter.TLabel", background=BG, foreground=FG_MATT,
                       font=("Segoe UI", 10))
        stil.configure("Titel.TLabel", background=BG_KARTE, foreground=FG,
                       font=("Segoe UI Semibold", 12))
        stil.configure("Matt.TLabel", background=BG_KARTE, foreground=FG_MATT,
                       font=("Segoe UI", 9))
        stil.configure("TButton", font=("Segoe UI Semibold", 10), borderwidth=0,
                       padding=(16, 9), background=BG_FELD, foreground=FG)
        stil.map("TButton", background=[("active", LINIE)])
        stil.configure("Akzent.TButton", background=AKZENT, foreground="#ffffff")
        stil.map("Akzent.TButton", background=[("active", AKZENT_D),
                                               ("disabled", LINIE)])
        stil.configure("Balken.Horizontal.TProgressbar", background=AKZENT,
                       troughcolor=BG_FELD, borderwidth=0, lightcolor=AKZENT,
                       darkcolor=AKZENT)

    def _aufbau(self):
        kopf = tk.Frame(self, bg=BG)
        kopf.pack(fill="x", padx=22, pady=(20, 6))
        ttk.Label(kopf, text="Newsbot", style="Kopf.TLabel").pack(anchor="w")
        ttk.Label(kopf,
                  text="KI, RPA, Automatisierung, Rechenzentren, Investitionen, Big Tech",
                  style="Unter.TLabel").pack(anchor="w", pady=(2, 0))

        karte = tk.Frame(self, bg=BG_KARTE, highlightbackground=LINIE,
                         highlightthickness=1)
        karte.pack(fill="both", expand=True, padx=22, pady=(14, 0))

        zeile = tk.Frame(karte, bg=BG_KARTE)
        zeile.pack(fill="x", padx=18, pady=(16, 2))
        ttk.Label(zeile, text="Sammellauf", style="Titel.TLabel").pack(side="left")
        self.knopf = ttk.Button(zeile, text="Nachrichten sammeln",
                                style="Akzent.TButton", command=self.starten)
        self.knopf.pack(side="right")
        self.knopf_ordner = ttk.Button(zeile, text="Ordner oeffnen",
                                       command=self.ordner_oeffnen)
        self.knopf_ordner.pack(side="right", padx=(0, 10))

        regler = tk.Frame(karte, bg=BG_KARTE)
        regler.pack(fill="x", padx=18, pady=(6, 2))
        self.je_quelle = tk.IntVar(value=MAX_JE_QUELLE)
        self.stunden = tk.IntVar(value=STUNDEN_ZURUECK)
        ttk.Label(regler, text="Meldungen je Quelle").pack(side="left")
        ttk.Spinbox(regler, from_=5, to=100, increment=5, width=5,
                    textvariable=self.je_quelle).pack(side="left", padx=(8, 22))
        ttk.Label(regler, text="Zeitraum in Stunden").pack(side="left")
        ttk.Spinbox(regler, from_=6, to=168, increment=6, width=5,
                    textvariable=self.stunden).pack(side="left", padx=(8, 0))
        ttk.Label(regler,
                  text="mehr Stunden holt auch Quellen herein, die selten veroeffentlichen",
                  style="Matt.TLabel").pack(side="left", padx=(18, 0))

        self.balken = ttk.Progressbar(karte, style="Balken.Horizontal.TProgressbar",
                                      mode="determinate")
        self.balken.pack(fill="x", padx=18, pady=(4, 10))

        self.ausgabe = scrolledtext.ScrolledText(
            karte, bg=BG_FELD, fg=FG, insertbackground=FG, relief="flat",
            font=("Consolas", 10), padx=14, pady=12, wrap="word",
            highlightbackground=LINIE, highlightthickness=1)
        self.ausgabe.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.schreiben(
            "Bereit.\n\n"
            "Ein Klick auf 'Nachrichten sammeln' geht alle Quellen aus quellen.txt\n"
            "durch, filtert nach deinen Themen und legt das Ergebnis im Unterordner\n"
            "'news' ab - einmal mit Datum im Namen und einmal als latest.md.\n\n"
            "Danach Claude Bescheid sagen: die Datei wird gelesen und daraus\n"
            "entstehen zwei Entwuerfe - einer fuer X, einer fuer Viva Engage.\n")

        fuss = tk.Frame(self, bg=BG)
        fuss.pack(fill="x", padx=22, pady=(8, 18))
        self.status = tk.Label(fuss, text="", bg=BG, fg=FG_MATT,
                               font=("Segoe UI", 9), anchor="w")
        self.status.pack(fill="x")

    # -- Hilfen ------------------------------------------------------------
    def schreiben(self, text):
        self.ausgabe.insert("end", text + "\n")
        self.ausgabe.see("end")

    def _queue_pruefen(self):
        try:
            while True:
                art, nutzlast = self.nachrichten.get_nowait()
                if art == "text":
                    self.schreiben(nutzlast)
                elif art == "status":
                    self.status.configure(text=nutzlast)
                elif art == "balken":
                    self.balken["value"] = nutzlast
                elif art == "max":
                    self.balken["maximum"] = nutzlast
                elif art == "fertig":
                    self.knopf.configure(state="normal")
                elif art == "fehler":
                    messagebox.showerror("Fehler", nutzlast)
        except queue.Empty:
            pass
        self.after(120, self._queue_pruefen)

    def melden(self, art, nutzlast):
        self.nachrichten.put((art, nutzlast))

    def ordner_oeffnen(self):
        os.makedirs(AUSGABE, exist_ok=True)
        try:
            os.startfile(AUSGABE)  # noqa: SIM115  (nur Windows)
        except AttributeError:
            messagebox.showinfo("Ordner", AUSGABE)

    # -- Sammellauf --------------------------------------------------------
    def starten(self):
        self.knopf.configure(state="disabled")
        self.ausgabe.delete("1.0", "end")
        try:
            je_quelle = max(5, int(self.je_quelle.get()))
            stunden = max(6, int(self.stunden.get()))
        except Exception:
            je_quelle, stunden = MAX_JE_QUELLE, STUNDEN_ZURUECK
        threading.Thread(target=self._arbeit, args=(je_quelle, stunden),
                         daemon=True).start()

    def _arbeit(self, je_quelle, stunden):
        try:
            anzahl_quellen = len(quellen_lesen())
        except Exception as fehler:  # noqa: BLE001
            self.melden("fehler", str(fehler))
            self.melden("fertig", None)
            return

        self.melden("max", anzahl_quellen)

        def fortschritt(nummer, gesamt, name):
            self.melden("status", "{} / {}  -  {}".format(nummer, gesamt, name))
            self.melden("balken", nummer)

        try:
            pfad, anzahl = sammeln(je_quelle, stunden,
                                   melden=lambda t: self.melden("text", t),
                                   fortschritt=fortschritt)
        except Exception as fehler:  # noqa: BLE001
            self.melden("fehler", str(fehler))
            self.melden("fertig", None)
            return

        if pfad:
            self.melden("text", "\n{} Meldungen gespeichert:".format(anzahl))
            self.melden("text", "  " + os.path.basename(pfad))
            self.melden("text", "  news/latest.md")
            self.melden("text",
                        "\nJetzt Claude Bescheid sagen - die Datei wird gelesen und\n"
                        "daraus entstehen die beiden Entwuerfe.")
            self.melden("status", "Fertig - {} Meldungen".format(anzahl))
        self.melden("fertig", None)


def kommandozeile():
    """Fassung ohne Fenster - fuer Server und GitHub Actions."""
    import argparse
    zerleger = argparse.ArgumentParser(description="Newsbot ohne Oberflaeche")
    zerleger.add_argument("--cli", action="store_true", help="ohne Fenster laufen")
    zerleger.add_argument("--je-quelle", type=int, default=MAX_JE_QUELLE)
    zerleger.add_argument("--stunden", type=int, default=STUNDEN_ZURUECK)
    zerleger.add_argument("--quellen", default=None,
                          help="andere Quellendatei, z. B. gesetze_quellen.txt")
    zerleger.add_argument("--ausgabe", default=None,
                          help="anderer Ausgabeordner, z. B. gesetze")
    zerleger.add_argument("--titel", default=None,
                          help="Ueberschrift der Digest-Datei")
    zerleger.add_argument("--alles", action="store_true",
                          help="ohne Themenfilter - alles Frische behalten")
    zerleger.add_argument("--themen", choices=["technik", "recht"], default="technik",
                          help="welcher Themensatz gilt: technik (Standard) oder recht")
    argumente = zerleger.parse_args()

    global QUELLDATEI, AUSGABE, TITEL, OHNE_FILTER
    if argumente.quellen:
        QUELLDATEI = os.path.join(ORDNER, argumente.quellen)
    if argumente.ausgabe:
        AUSGABE = os.path.join(ORDNER, argumente.ausgabe)
    if argumente.titel:
        TITEL = argumente.titel
    OHNE_FILTER = argumente.alles

    global _MUSTER
    if argumente.themen == "recht":
        _MUSTER = muster_bauen(RECHT)
    pfad, anzahl = sammeln(argumente.je_quelle, argumente.stunden, melden=print)
    if pfad:
        print("\n{} Meldungen gespeichert in {}".format(anzahl, pfad))
        return 0
    print("\nNichts gefunden.")
    return 1


if __name__ == "__main__":
    import sys
    if "--cli" in sys.argv or not OBERFLAECHE:
        sys.exit(kommandozeile())
    Newsbot().mainloop()
