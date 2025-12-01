## ADR 0001 – Grundstruktur des Datenmodells

### Status

Entwurf (kann angepasst/erweitert werden)

### Kontext

Das System verarbeitet Daten aus unterschiedlichen Quellen (z.B. Demo-Tabellen aus `infra/migrations`) und soll diese:

- konsolidieren (z.B. Kunden aus verschiedenen Systemen),
- mit Identitätslogik zusammenführen,
- mit semantischen Informationen (Begriffe, KPIs) anreichern,
- und über API-Gateway & Cockpit nutzbar machen.

Es stellt sich die Frage, wie wir das Datenmodell grundsätzlich strukturieren:

- Stark quellenorientiert (jedes Quellsystem „spricht“ in seinem eigenen Schema).
- Stark harmonisiert (frühe Transformation in ein einheitliches, fachliches Modell).
- Hybride Ansätze (Staging + harmonisiertes Kernmodell).

### Entscheidung

Wir wählen einen **hybriden Ansatz** mit folgenden Ebenen:

1. **Quell-/Staging-Ebene**
   - Tabellen nahe an der Quelle (z.B. Demo-Source-Tabellen, Staging-Kandidaten).
   - Ziel: Verluste bei der Übernahme minimieren, Schema-Änderungen der Quelle nachvollziehen.

2. **Harmonisiertes Kernmodell**
   - Fachlich ausgerichtete Entitäten (z.B. `customer`, `scan_run`).
   - Identity-Resolution findet auf/nahe dieser Ebene statt.

3. **Semantische Ebene**
   - Begriffe, KPIs und deren Zuordnung zu Feldern im Kernmodell.

### Begründung

- **Flexibilität**: Neue Quellen können zunächst in die Staging-Ebene integriert werden, ohne sofort das Kernmodell zu ändern.
- **Lesbarkeit**: Fachliche Nutzer und Downstream-Systeme arbeiten mit einem konsistenten Kernmodell.
- **Nachvollziehbarkeit**: Über Staging-Tabellen bleibt ersichtlich, aus welcher Quelle welche Informationen stammen.

### Konsequenzen

- Höherer initialer Aufwand für Design und Pflege des Kernmodells.
- Notwendigkeit von klar dokumentierten Mappings (Quelle → Staging → Kernmodell), siehe `docs/data-model.md`.
- Migrationsskripte (`infra/migrations`) sollten diese Ebenen explizit widerspiegeln und kommentieren.


