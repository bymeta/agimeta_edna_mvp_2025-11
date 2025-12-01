## Roadmap & Ideen

Dieses Dokument sammelt geplante Features, technische Aufgaben und Ideen.

### Kurzfristig (0–4 Wochen)

- [ ] **Scans & Quellen transparenter machen**
  - Bessere Darstellung von Datenquellen und deren Status im Cockpit.
  - Verlinkung zu Metadaten (Quelle, letzter Scan, Anzahl Objekte).

- [ ] **Datenmodell schärfen**
  - Harmonisiertes Kundenmodell konkretisieren (siehe `docs/data-model.md`).
  - Erste Mappings von Demo-Quellen definieren.

### Mittelfristig (1–3 Monate)

- [ ] **Identity-Resolution verbessern**
  - Matching-Strategien (regelbasiert vs. ML-basiert) ausprobieren.
  - Transparente Erklärung, warum zwei Objekte gematcht wurden.

- [ ] **Semantik & KPIs ausbauen**
  - Mehr KPIs und Begriffe definieren und im Cockpit sichtbar machen.
  - Versionierung und Freigabeprozess für Begriffe/KPIs definieren.

### Langfristig

- [ ] **Skalierung & Performance**
  - Asynchrone Kommunikation zwischen Services (Queue / Eventing).
  - Skalierung der Worker und des Scanners unter Last testen.

- [ ] **Self-Service & Konfiguration**
  - UI für das Registrieren neuer Datenquellen.
  - Konfiguration von Mappings und KPIs durch Fachanwender.

> Dieses Dokument ist bewusst „leichtgewichtig“ gedacht – einfach anpassen, ergänzen und streichen.


