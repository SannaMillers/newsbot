# Newsbot

Sammelt auf Knopfdruck die Schlagzeilen zu KI, KI-Regulierung, RPA und
Automatisierung, Rechenzentren, Investitionen, Big Tech, Krypto, Energie,
Prozessen und Sicherheit — aus 32 Quellen, per RSS.

Das Ergebnis liegt in [`news/latest.md`](news/latest.md).

## Starten

1. Reiter **Actions**
2. links **Nachrichten sammeln**
3. rechts **Run workflow** → **Run workflow**

Nach ein bis zwei Minuten steht die neue Fassung in `news/`.

## Daraus die beiden Posts machen

In Claude schreiben:

> Lies https://raw.githubusercontent.com/BENUTZER/REPO/main/news/latest.md
> und schreib mir daraus zwei Beiträge:
> — einen für X, deutsch, maximal 280 Zeichen, zugespitzt, ohne Hashtags
> — einen für Viva Engage, **englisch**, sachlich und professionell, mit
>   konkretem Nutzen für Kolleginnen und Kollegen
> Beide sollen unterschiedliche Themen aufgreifen und sich nicht ähneln.

`BENUTZER/REPO` durch die eigenen Werte ersetzen.

## Quellen ändern

`quellen.txt`, eine Zeile je Quelle:

    Name | Kategorie | RSS-Adresse

Zeilen mit `#` am Anfang werden übersprungen. Quellen, die nicht antworten,
stehen am Ende jeder Digest-Datei mit Fehlergrund.

Für eigene Themensuchen eignet sich Google News:

    GN Meine Suche | Politik | https://news.google.com/rss/search?q=SUCHBEGRIFF%20when:3d&hl=de&gl=DE&ceid=DE:de

## Themen und Gewichtung

Stehen oben in `newsbot.py` im Abschnitt `THEMEN`. Die Muster sind reguläre
Ausdrücke; `\b` markiert eine Wortgrenze. Treffer im Titel zählen doppelt.

## Lokal

Dieselbe Datei läuft mit Fenster:

    python newsbot.py

oder ohne:

    python newsbot.py --cli --je-quelle 30 --stunden 36

## Wichtig

In dieses Repository gehören **keine Zugangsdaten**. Die Schlüssel für das
Veröffentlichen auf X bleiben auf dem eigenen Rechner.
