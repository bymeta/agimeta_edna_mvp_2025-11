## Datenmodell – Übersicht & Entwurfsnotizen

Dieses Dokument beschreibt das logische Datenmodell und dient als Ort für Entwurfsvarianten, Annahmen und Begründungen.

### Leitprinzipien

- **Quelle vs. harmonisiertes Modell**: Trennung von Quellschemata und einem konsolidierten, fachlichen Modell.
- **Nachvollziehbarkeit**: Jedes Feld im Zielmodell soll auf Quellenfelder zurückführbar sein.
- **Erweiterbarkeit**: Modell muss mit zusätzlichen Quellen und Domänen wachsen können.

### Bestehende Strukturen (Stand: Demo)

Aus den Migrationen unter `infra/migrations` ergeben sich aktuell u.a.:

- **Demo-Source-Tabellen** (z.B. Kundendaten, siehe `003_demo_source_table.sql`)
  - Repräsentieren „wie die Daten ankommen“.
  - Dürfen sich je Quelle unterscheiden (Spaltennamen, Typen, Kodierungen).

- **Objekt- / Kandidaten-Tabellen** (z.B. `002_object_candidates_staging.sql`)
  - Zwischenschicht für normalisierte Kandidaten, die aus verschiedenen Quellen stammen können.

- **Begriffe / KPIs / Semantik** (siehe `004_terms_and_kpis.sql`)
  - Tabellen für geschäftliche Begriffe, Kennzahlen und deren Definitionen.

### Zielmodell (fachliches Modell)

**Idee**: Ein zentrales, fachlich orientiertes Modell aufbauen, z.B. für die Domäne „Kunde“:

- **Entitäten**
  - `customer` (harmonisierter Kunde, inkl. Identity-Resolution)
  - `customer_source_record` (Verknüpfung zu Quellsystemen und Rohdaten)
  - `scan` / `scan_run` (Kontext, wann/wie Daten gelesen wurden)

- **Beziehungen**
  - 1 `customer` : N `customer_source_record`
  - 1 `scan_run` : N `customer_source_record`

> Hier kannst du Skizzen (z.B. ER-Diagramme) oder Varianten dokumentieren.

### Mapping Quelle → Ziel

Für jede Quelle (z.B. Demo-Tabelle) sollte es eine dokumentierte Abbildung geben:

- **Beispielstruktur pro Quelle**
  - Name der Quelle
  - Tabelle(n) in der Datenbank
  - Feld-Mapping: Quellspalte → Zielattribut
  - Bereinigungs-/Transformationslogik (z.B. Trimmen, Normalisieren von Länder-/Regionencodes)

Empfehlung: Pro Quelle ein Abschnitt in diesem Dokument oder eine eigene Datei unter `docs/data-sources/`.

### Semantik, Begriffe & KPIs

- **Begriffe**
  - Zentrale Business-Terme (z.B. „Aktiver Kunde“, „Churn“, „MRR“).
  - Beschreibung, Verantwortlicher, Gültigkeitsbereich, Versionierung.

- **KPIs**
  - Technische Definition (Formel, Filter).
  - Verknüpfung zu Tabellen/Spalten im Datenmodell.

> Idee: Pro KPI einen Eintrag, der sowohl in der DB (Migration `004_terms_and_kpis.sql`) als auch hier beschrieben wird.

### MVP-Tabellen (aus `006_mvp_customer_hub.sql`)

Für den MVP wurden folgende Kern-Tabellen ergänzt, die das vereinfachte Kunden-Hub-Modell und den Full-Scan light abbilden:

- **`scan_run`**
  - Repräsentiert einen Lauf des Scanners (Quelle, Status, Start/Ende, `metrics_json`).
  - Dient als Anker für Profiling-Informationen und KPIs.

- **`scan_profile_table`**
  - Aggregierte Profiling-Daten pro Tabelle (z.B. `row_count`, `sample_hash`).
  - Zeigt, welche Tabellen im Rahmen eines `scan_run` tatsächlich betrachtet wurden.

- **`scan_profile_column`**
  - Profiling-Daten pro Spalte: `distinct_count`, `null_count`, `null_rate`, Datentyp.
  - Grundlage für spätere DQ-/Profiling-Features.

- **`object_customer`**
  - Harmonisiertes Kundenobjekt (Golden Customer) mit Kernfeldern (`name`, `email`, `tax_id`, `country`).
  - Feld `source_expr` beschreibt, wie Attribute aus Quellen abgeleitet wurden (Lineage-Hook).

- **`object_customer_source_link`**
  - Verknüpft `object_customer` mit Quellzeilen (`source_system`, `source_table`, `source_pk`).
  - Enthält `match_rule`, `confidence`, `explanation` – Basis für transparente Identity-Resolution.

- **`kpi_fact`**
  - Speichert berechnete KPIs pro `scan_run` (z.B. Dublettenquote, fehlende `tax_id`/`email`).
  - Ermöglicht einfache Auswertung im Cockpit und historische Vergleiche.

- **`event_raw` / `event_normalized`**
  - Vorbereitete Tabellen für Event-Ingestion (Roh-Events und normalisierte Events).
  - Im MVP primär als „Zukunftshaken“ gedacht; die eigentliche Befüllung kann in späteren Phasen erfolgen.

### Offene Designfragen

- Wie strikt sollen Quellen transformiert werden (ELT vs. ETL)?
- Sollen historische Zustände (SCD-Typen) im Zielmodell abgebildet werden?
- Wie wird mit sich ändernden Schemas in Quellsystemen umgegangen?


