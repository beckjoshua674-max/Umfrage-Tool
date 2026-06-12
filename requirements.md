# Projektanforderungen: Umfrage-Tool (Evaluation „Ask Alma“)

## 1. Projektübersicht (Modul: Verteilte Systeme)
Entwicklung einer Web-Anwendung zur Durchführung von Umfragen im Rahmen des Moduls **„Verteilte Systeme“**. Der initiale Fokus liegt auf der Evaluation des Nutzens des KI-Tools „Ask Alma“. 
Aufgrund des Modulkontexts muss das System zwingend verteilte Architekturprinzipien (z. B. saubere Client-Server-Trennung, lose Kopplung über Schnittstellen) aufweisen. Das System muss generisch aufgebaut sein, um perspektivisch für beliebige weitere Umfragen nutzbar zu sein.

## 2. Projektmanagement & Multi-Agenten-Workflow
* **KI-Tool-Stack:** Die Entwicklung und Planung erfolgt im Zusammenspiel der KI-Systeme **Codex** und **Antigravity**. 
* **Single Source of Truth:** Diese `requirements.md` ist das zentrale Synchronisationsdokument für beide Tools. Vor jeder neuen Implementierungsphase ist der aktuelle Stand dieses Dokuments auszulesen.
* **Update-Pflicht:** Sobald Anforderungen im Projektverlauf (egal mit welchem Tool) verfeinert oder geändert werden, ist diese Datei zwingend und umgehend zu aktualisieren.
* **Timebox für den ersten Prototyp (V1):** max. 1–2 Stunden.

## 3. Architektur & Prinzipien Verteilter Systeme (Fokus V1)
* **Client-Server-Architektur:** Das System muss aus einem strikt getrennten Frontend (Client) und einem Backend (Server) bestehen.
* **Schnittstellen-Kommunikation:** Der Datenaustausch zwischen Client und Server erfolgt zustandslos (stateless) über eine definierte API (RESTful oder vergleichbar) im JSON-Format.
* **Trennung von Logik und Daten:** Die Umfrage-Definitionen (Fragen, Antwortmöglichkeiten) werden als JSON-Konfiguration vom Backend verwaltet und dynamisch über die API an den Client ausgeliefert.

## 4. Funktionale Anforderungen (Prototyp V1)
* **Umfrage-Engine (Client):** Dynamischer Aufbau des Fragebogens basierend auf der API-Antwort. Unterstützung für Freitext, Multiple-Choice und Likert-Skalen. Navigation durch die Umfrage.
* **Datenspeicherung (Server):** Ein API-Endpunkt (z. B. `POST /api/results`), der die Antworten vom Client entgegennimmt und speichert (für V1 reicht eine lokale Dateiablage als JSON/CSV oder eine leichtgewichtige Datenbank wie SQLite).

## 5. UI & Design (Corporate Identity)
* Das Frontend muss sich am Corporate Design der Hochschule orientieren.
* **Referenz:** https://www.hs-kehl.de/
* Das Design (Farbschema, Typografie) der Referenzseite ist via CSS auf das Umfrage-Tool anzuwenden.

## 6. Zukünftige Ausbaustufen (Out of Scope für V1)
* **Containerisierung:** Bereitstellung von Client, Server und Datenbank als unabhängige Docker-Container.
* **Automatisierung:** Vollautomatisierte Dokumentation und Agenten-Steuerung via `Agents.md`.
* **Microservices:** Auslagerung von Diensten (z. B. Authentifizierung, Daten-Auswertung).