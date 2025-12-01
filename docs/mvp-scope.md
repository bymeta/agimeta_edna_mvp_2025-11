## MVP Scope – Customer Data Hub (Phase 1)

Dieses Dokument beschreibt den präzisen Scope des ersten MVP-Slices.

### Zielbild Phase 1

- **End-to-End-Slice** für die Domäne **Kunde** (optional Lieferant später).
- In **wenigen Tagen** lauffähig: Von Demo-Quelle → Scan → Golden Customers → einfache KPIs im Cockpit.
- Dient als Referenz-Implementierung für spätere Erweiterungen (weitere Quellen, Domänen, DQ, Lineage).

### In Scope (funktional)

- **Datenquellen**
  - Mindestens eine **Demo-SQL-Quelle** mit Kundendaten (bestehend oder per Migration z.B. `003_demo_source_table.sql`).
  - Zusätzlich: Möglichkeit, **beliebige weitere PostgreSQL-Datenbanken** zu registrieren:
    - Konfiguration über die Tabelle `edna_source_databases` (Host, Port, DB-Name, User, Passwort, Schemas).
    - Der Scanner liest diese Konfiguration und scannt alle als `active = TRUE` markierten Quellen.
  - Fokus für die MVP-Demo weiterhin auf einfachen Customer-Feldern: `source_customer_id`, `name`, `email`, `tax_id`, `country`.

- **Scans (inkl. Full-Scan light)**
  - Start eines **Scan-Runs** für die Demo-Quelle (per API oder Cockpit).
  - Persistenz eines Scan-Kontexts (`scan_run`) mit Status, Laufzeiten und Kennzahlen (`metrics_json`).
  - **Full-Scan light** der Demo-DB:
    - Scanner inventarisiert alle Tabellen & Spalten der Demo-Datenbank.
    - Schreibt Profiling-Statistiken in `scan_profile_table` / `scan_profile_column` (z.B. `row_count`, `null_rate`, `distinct_count`, `sample_hash`).
    - Golden-Build nutzt davon nur die relevanten Felder, der Rest dient als Nachweis „Full-Scan“.

- **Customer Hub (Golden Customers)**
  - Konsolidierte **Golden-Customer-Tabelle** (`object_customer`).
  - Verknüpfungstabelle zwischen Golden Customer und Quellzeilen (`object_customer_source_link`).
  - **Deterministisches Matching**:
    - Priorität: `tax_id` exakt,
    - Fallback: `email` (einfacher String-Vergleich oder sehr simpler Fuzzy-Match),
    - weiterer Fallback: Kombination aus `name` + `country`.
  - **Transparenz / HiTL-ready**:
    - In `object_customer_source_link` werden `match_rule` (z.B. `tax_id`, `email`, `name_country`), `confidence` und `explanation` (z.B. „tax_id exact“, „email normalized eq“) gespeichert.
    - Basis für spätere Human-in-the-Loop-Freigaben.

- **Semantik & KPIs (Light)**
  - Kleine Menge fester **Glossar-Terme** (z.B. `CUSTOMER`, `ACTIVE_CUSTOMER`, `DUPLICATE_RATE`).
  - Mindestens **2–3 MVP-KPIs**, z.B.:
    - Anteil doppelter Kunden (Dublettenquote).
    - Anzahl Quell-Systeme pro Customer.
    - Anzahl Kunden ohne Steuer-ID / ohne E-Mail.
  - Persistenz der KPI-Werte in einer einfachen Faktentabelle `kpi_fact`:
    - `kpi_key`, `value`, `scan_run_id`, `computed_at`.

- **Cockpit UI (Minimal, mit maximalem Lerneffekt)**
  - **Scan-Übersicht**:
    - Liste von `scan_run`-Einträgen (Queue/History) mit Status, Start/Ende.
    - Profiling-Kacheln aus `scan_profile_*` (z.B. Anzahl Tabellen, Felder, Durchschnitts-Null-Rate).
  - **Customer-Übersicht**:
    - Tabelle der Golden Customers mit Basisfeldern und KPIs (z.B. Anzahl Quell-Sätze pro Customer).
  - **Customer-Detailansicht**:
    - Anzeige des Golden Records (inkl. `source_expr` und ggf. `rule_id` je Attribut als „Lineage-Hook“).
    - Darunter Liste der zugehörigen Quellzeilen (inkl. Matching-Regel, `match_rule`, `confidence`, `explanation`).

### In Scope (technisch)

- Nutzung des bestehenden Stacks:
  - Backend über `apps/api-gateway` (+ Scanner-Logik in `apps/scanner`).
  - Frontend `apps/cockpit` (Next.js).
  - Postgres aus `docker-compose.yml` als zentrale DB.
- Einfache, synchrone oder „best effort“ asynchrone Verarbeitung:
  - Ein Worker/Prozess genügt für MVP (kein verteiltes Queue-Setup notwendig).
- **Scanner-Betrieb primär in Docker**
  - Alle Services (Postgres, API-Gateway, Scanner, Identity, Semantic) laufen regulär als Docker-Container (`make up`).
  - Lokale `uv`-Runs werden primär für Migrationen und Debugging genutzt, nicht für produktive Scans.
- **Host/Port-Konvention für Source-Datenbanken**
  - Für lokale PostgreSQL-Instanzen, die vom Scanner-Container erreicht werden sollen:
    - Host: `host.docker.internal`
    - Port: `5433` (oder der jeweils gemappte Host-Port in `docker-compose.yml`).
  - Für lokale Debug-Scans mit `uv run -m apps.scanner...`:
    - Host: `localhost`
    - Port: `5433`.
- **Events- und Lineage-Hooks (Zukunftshaken)**
  - Anlegen minimaler Event-Tabellen (z.B. `event_raw`, `event_normalized`) inkl. `case_key_hint`.
    - Im MVP reicht ein definiertes Schema + Insert-API; aktives Befüllen ist optional.
  - Pro Attribut im Golden Customer Speicherung eines `source_expr` (z.B. `coalesce(s1.name,s2.name)`) und optional `rule_id`.
    - Diese Metadaten dienen später als Grundlage für Lineage-Kanten und DQ-Regeln.

### Minimal-Datenmodell (Phase 1)

Im MVP werden folgende Tabellen erwartet (vereinfachte Sicht):

- `scan_run`  
  - `id`, `source_system`, `status`, `started_at`, `ended_at`, `metrics_json`.

- `scan_profile_table` / `scan_profile_column`  
  - Profiling-Informationen pro Tabelle/Spalte: `row_count`, `distinct_count`, `null_rate`, optionale Samples/Hashes.

- `object_customer`  
  - `customer_id`, `name`, `email`, `tax_id`, `country`, `source_expr`, `created_at`, `updated_at`.

- `object_customer_source_link`  
  - `customer_id`, `source_system`, `source_table`, `source_pk`, `match_rule`, `confidence`, `explanation`.

- `kpi_fact`  
  - `kpi_key`, `value`, `scan_run_id`, `computed_at`.

### API-Schnitt (minimal, stabil)

Folgende HTTP-Endpunkte werden als stabiler Kern für das MVP definiert:

- `POST /scan-runs`
  - Startet einen neuen Scan-Run für die Demo-Quelle.
- `GET /scan-runs`
  - Paginierte Liste der Scan-Runs inkl. Status und Basis-Metriken.
- `GET /customers`
  - Liefert Golden Customers (mit Filtermöglichkeiten, z.B. nach Land, Dublettenstatus).
- `GET /customers/{id}`
  - Liefert einen Golden Customer inkl. aller `object_customer_source_link`-Einträge (mit `match_rule`, `confidence`, `explanation`).
- `GET /kpis`
  - Liefert die MVP-KPIs (z.B. Duplicate-Rate, fehlende `tax_id`/`email`, Anzahl Quellen pro Customer) aus `kpi_fact`.

Es gibt im MVP **keine** API für manuelle Merge-/Split-Operationen; alle Merges erfolgen deterministisch im Job.

### Out of Scope für Phase 1

- **Kein vollständiger generischer Objekt-Hub**:
  - Keine vollständige Umsetzung aller Tabellen aus dem großen DatenDictionary.
  - Kein generisches EAV für alle Attribute nötig – konkrete Spalten für Kunden reichen.

- **Kein vollständiges DQ-Framework**
  - Keine generischen `dq_rule`-/`dq_result`-Tabellen.
  - Nur einfache, im Code berechnete Qualitätsindikatoren/KPIs.

- **Keine voll ausgebaute Governance/Access-Control**
  - Minimaler AuthN/AuthZ-Ansatz ausreichend (z.B. einfache Rollen; kein komplettes ABAC/Policy-System).

- **Keine vollständige Lineage-Schicht**
  - Noch keine `lineage_node`-/`lineage_edge`-Implementierung.
  - Nur einfache, nachvollziehbare Pfade (z.B. via `object_customer_source_link` und `source_expr`).

- **Kein Multi-Tenant-SaaS-Betrieb**
  - Fokus auf einen Tenant/Stack (z.B. Demo-Mandant).
  - `tenant_id` kann bereits im Schema vorgesehen sein, aber es gibt **keinen** Anspruch auf Multi-Tenant-Isolation im MVP.

### Akzeptanzkriterien (messbar)

- **Full-Scan-Nachweis**
  - 100 % Tabellen der Demo-DB sind in `scan_profile_*` mit mindestens `row_count` und `null_rate` erfasst.
- **Golden-Build-Qualität**
  - ≥ 98 % der relevanten Datensätze werden deterministisch einer Golden-ID zugeordnet; Duplicate-Rate ist als KPI sichtbar.
- **Transparenz**
  - Jeder Link in `object_customer_source_link` enthält `match_rule`, `confidence` und `explanation`.
- **UI-Funktionalität**
  - Scan-Runs werden gelistet; Golden-Liste und -Detail sind aufrufbar; mindestens 2–3 KPIs werden im Cockpit dargestellt.
- **API-Stabilität**
  - Obige Endpunkte funktionieren idempotent; Antwortzeiten für `GET /customers` (Liste, 50 Items) liegen typischerweise < 500 ms.

### Abgrenzung zu späteren Phasen

- **Phase 2** (nach erstem Kundenfeedback):
  - Ausbau des Datenmodells (weitere Domänen, saubereres EAV, mehr Quelltypen).
  - Einführung eines flexibleren DQ- und Governance-Layers.

- **Phase 3**:
  - Vollständige Lineage, Multi-Tenant-SaaS-Betrieb, umfangreiche Governance & Policies.

> Dieses Dokument beschreibt bewusst nur den **MVP-Scope**. Für das langfristige Zielbild siehe `docs/architecture.md`, `docs/data-model.md` und die ADRs in `docs/adr/`.


