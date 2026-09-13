# Newsbot

Zwei Sammelläufe, ein Knopf.

**Technik und Wirtschaft** — KI, KI-Regulierung, RPA und Automatisierung,
Rechenzentren, Investitionen, Big Tech, Krypto, Energie, Prozesse,
Sicherheit. Aus 32 Quellen, per RSS.
Ergebnis: [`news/latest.md`](news/latest.md)

**Gesetze und Verordnungen** — neue Regelungen und Änderungen in
Deutschland und der EU, aus amtlichen Quellen: Bundesgesetzblatt
(recht.bund.de), Bundestag, Bundesregierung, EUR-Lex, EU-Kommission,
dazu Themensuchen.
Ergebnis: [`gesetze/latest.md`](gesetze/latest.md)

## Starten

1. Reiter **Actions**
2. links **Nachrichten sammeln**
3. rechts **Run workflow** → **Run workflow**

Nach ein bis zwei Minuten stehen beide neuen Fassungen im Repository.
Zusätzlich läuft der Workflow täglich um 05:12 UTC (07:12 deutscher
Sommerzeit) von allein.

## Daraus die Beiträge machen

Für Technik und Wirtschaft, in Claude schreiben:

> Lies https://raw.githubusercontent.com/SannaMillers/newsbot/main/news/latest.md
> und schreib mir daraus zwei Beiträge:
> — einen für X, deutsch, maximal 280 Zeichen, zugespitzt, ohne Hashtags
> — einen für Viva Engage, **englisch**, sachlich und professionell, mit
>   konkretem Nutzen für Kolleginnen und Kollegen
> Beide sollen unterschiedliche Themen aufgreifen und sich nicht ähneln.

Für die Rechtslage:

> Lies https://raw.githubusercontent.com/SannaMillers/newsbot/main/gesetze/latest.md
> und schreib mir einen Beitrag zu der wichtigsten Neuerung: Wen betrifft
> sie, ab wann, was ändert sich konkret. Wäge Vor- und Nachteile kritisch
> ab und nenne, wer davon profitiert und wer die Kosten trägt.

## Quellen ändern

`quellen.txt` (Technik) und `gesetze_quellen.txt` (Recht), eine Zeile je
Quelle:

    Name | Kategorie | RSS-Adresse

Zeilen mit `#` am Anfang werden übersprungen. Quellen, die nicht
antworten, stehen am Ende der jeweiligen Digest-Datei mit Fehlergrund.

Für eigene Themensuchen eignet sich Google News:

    GN Meine Suche | Politik | https://news.google.com/rss/search?q=SUCHBEGRIFF%20when:3d&hl=de&gl=DE&ceid=DE:de

## Themen und Gewichtung

Stehen oben in `newsbot.py`: `THEMEN` für den Technik-Lauf, `RECHT` für
den Gesetzes-Lauf. Die Muster sind reguläre Ausdrücke; `\b` markiert eine
Wortgrenze. Treffer im Titel zählen doppelt.

Amtliche Feeds wie das Bundesgesetzblatt lassen die Beschreibung leer und
liefern den Kontext in eigenen Feldern. Die stehen in `ZUSATZFELDER` und
landen im Digest als `Typ | Initiant | Fundstelle | Sachgebiet`.

## Lokal

Dieselbe Datei läuft mit Fenster:

    python newsbot.py

oder ohne:

    python newsbot.py --cli --je-quelle 30 --stunden 36
    python newsbot.py --cli --quellen gesetze_quellen.txt --ausgabe gesetze \
        --titel "Rechtslage" --themen recht --je-quelle 30 --stunden 96

## Wichtig

In dieses Repository gehören **keine Zugangsdaten**. Die Schlüssel für das
Veröffentlichen auf X bleiben auf dem eigenen Rechner.
