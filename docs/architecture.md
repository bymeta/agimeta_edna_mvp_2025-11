## Architekturübersicht

Dieses Dokument beschreibt die Gesamtarchitektur des EDNA-Systems und wie die einzelnen Services zusammenspielen.

### Ziele der Architektur

- **Modulare Services**: Trennung von Scannen, Identitätsfindung, Semantik und API-Gateway.
- **Skalierbarkeit**: Arbeiter (z.B. Scanner, Identity-Worker) können unabhängig skaliert werden.
- **Nachvollziehbarkeit**: Klare Verantwortlichkeiten und Datenflüsse.

### Services

- **`apps/api-gateway`**
  - Bereitstellung einer zentralen HTTP-API.
  - Orchestriert Aufrufe an Scanner, Identity und Semantik.

- **`apps/scanner`**
  - Liest Datenquellen (z.B. Demo-Tabellen aus `infra/migrations`).
  - Erkennt Objekte/Kandidaten und schreibt sie in die Datenbank.

- **`apps/identity` & `apps/identity-worker`**
  - Matching und Zusammenführung von Objekten/Entitäten (z.B. Kunden).
  - Auslagerung rechenintensiver Aufgaben in Worker-Prozesse.

- **`apps/semantic`**
  - Anreicherung von Daten mit semantischen Informationen (z.B. KPIs, Begriffe).

- **`apps/cockpit`**
  - Next.js-Frontend für die Visualisierung und Steuerung (Scans, Objekte, Datenbanken).

- **`packages/edna-common`**
  - Gemeinsame Komponenten wie Config, Logging, Datenbankzugriff und Datenmodelle.

### Datenfluss (High-Level)

1. **Quellen registrieren**  
   - Metadaten zu Quellsystemen (z.B. Demo-Tabellen) werden über Migrationen in der Datenbank angelegt (`infra/migrations`).

2. **Scans auslösen**  
   - Über das Cockpit oder die API werden Scans gestartet.
   - Der Scanner liest die registrierten Quellen und schreibt Ergebnisse in Staging-/Ergebnis-Tabellen.

3. **Identitätsabgleich & Semantik**  
   - Identity-Services führen Objekte zusammen.
   - Semantic-Service reichert Daten mit Begriffen/KPIs an.

4. **Nutzung im Cockpit**  
   - Cockpit greift über das API-Gateway auf konsolidierte und semantisch angereicherte Daten zu.

### Offene Fragen / Ideen

- Welche Queuing-/Messaging-Technologie soll langfristig zwischen Services genutzt werden?
- Wie granular sollen Scans (zeitlich, nach Quelle, nach Objektart) steuerbar sein?
- Wie wird Versionierung des Datenmodells und der Semantik gehandhabt?


