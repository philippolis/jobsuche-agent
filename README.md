# Jobsuche Agent (Template)

KI-gestützte Jobsuche mit der `jobsuche-api` der Arbeitsagentur + OpenAI-Ranking.

Nutzen Sie dieses Repository als Ausgangspunkt für Ihren eigenen, personalisierten Job-Alert-Workflow.

## Was dieses Projekt macht

- Ruft aktuelle Stellenangebote über die API der Arbeitsagentur ab.
- Nutzt OpenAI, um basierend auf den Stellenbeschreibungen passende Jobs auszuwählen.
- Erstellt Markdown-Berichte im Ordner `reports/`.
- Verfolgt bereits vorgeschlagene Jobs im Ordner `data/`, um Duplikate zu vermeiden.
- Versendet optional Job-Berichte per E-Mail über GitHub Actions.

### Wie die KI-gestützte Suche funktioniert (und warum sie besser ist)

Jobportale basieren meist auf starren Keyword-Suchen. Das führt oft zu falschen Ergebnissen (z. B. wenn ein Keyword nur beiläufig erwähnt wird) oder verpassten Chancen (wenn ein passender Job voneinander abweichende, aber bedeutungsähnliche Begriffe verwendet). 

Dieses Projekt nutzt einen **zweistufigen, Token-effizienten KI-Prozess** (orchestriert in `scripts/main.py`), um Jobs intelligenter zu filtern:

1. **Stage 1 (Breite API-Suche & Shortlisting):** Das Skript ruft zunächst basierend auf den Parametern in `config/job_search_config.yml` neue Jobs über die Schnittstelle der Arbeitsagentur ab. Ein KI-Modell bewertet dann grob Jobtitel und Arbeitgeber anhand Ihres Profils (`config/candidate_profile.md`). Alles, was im Entferntesten passen könnte, wird großzügig in die engere Wahl (Shortlist) gezogen.
2. **Stage 2 (Deep Dive & Auswahl):** Für die Kandidaten der Shortlist werden nun die kompletten Stellenbeschreibungen geladen. Die KI liest die Ausschreibungen inklusive Beschreibungstext. Sie versteht den Kontext – zum Beispiel ob eine Technologie zwingend gefordert wird oder nur optional ist, ob es sich um eine interne Rolle statt Consulting handelt, und ob die Vertragsbedingungen (wie Unbefristung) passen.
3. **Individuelle Begründung:** Die KI wählt die besten Matches aus und generiert für jeden Job eine individuelle Begründung, die erklärt, *warum* diese Stelle perfekt zu den Anforderungen aus der Konfiguration passt.

Dadurch erhält man wesentlich präzisere, personalisierte Job-Vorschläge, die die Relevanz einer einfachen Keyword-Suche übertreffen.

## 1) Erstellen Sie Ihr eigenes Repo aus diesem Template

1. Klicken Sie auf GitHub auf **Use this template**.
2. Erstellen Sie Ihr eigenes Repository.
3. Klonen Sie Ihr neues Repo lokal.

## 2) Lokale Einrichtung

Abhängigkeiten installieren:

```bash
pip install -r requirements.txt
```

Fügen Sie Ihren OpenAI-Schlüssel zur Datei `.env` hinzu und konfigurieren Sie optional das verwendete Modell (Standard ist `gpt-5.2`):

```env
OPENAI_API_KEY=ihr_schluessel_hier
OPENAI_MODEL=gpt-5-mini # (oder gpt-5.2)
```

## 3) Personalisieren

Bearbeiten Sie diese Dateien:

- `config/candidate_profile.md` - Ihr Profil, Einschränkungen und Präferenzen
- `config/job_search_config.yml` - Suchbegriffe, Ort, Umkreis, Aktualität

## 4) Ausführen

```bash
python3 scripts/main.py
```

Ausgabe:

- `reports/job_report_<zeitstempel>.md`



## 5) Einrichtung des E-Mail Newsletters (optional)

Diese Vorlage enthält einen GitHub Actions Workflow, um Jobvorschläge per E-Mail zu erhalten:

- `.github/workflows/job_search.yml`: Geplante oder manuelle Ausführung, sendet den Bericht per E-Mail, committet neue Berichte.

### Automatisierter, geplanter E-Mail-Workflow (`job_search.yml`)

Standardzeitplan: jeden Samstag um `05:00 UTC` (passen Sie den Cron-Job bei Bedarf an).

Erforderliche Secrets:

- `OPENAI_API_KEY`
- `SMTP_SERVER_ADDRESS`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_TO_EMAIL`

Optionale SMTP-Secrets:

- `SMTP_SERVER_PORT` (Standard ist `587`)
- `SMTP_FROM_NAME` (Standard ist `Job Alert Agent`)

Einrichtungsschritte:

1. Fügen Sie die erforderlichen Secrets in Ihren GitHub Repository-Einstellungen hinzu.
2. Führen Sie den `Job Search Workflow` einmal manuell über den Tab **Actions** aus, um die E-Mail-Zustellung zu überprüfen.

### Beispiel: Generierter Job-Bericht

So sehen die generierten Job-Empfehlungen in der per GitHub Actions versendeten E-Mail aus. [Hier finden Sie eine generierte HTML-Beispiel-Email](examples/email_preview.html). 

Alternativ können Sie sich die HTML-Vorschau auch jederzeit lokal anzeigen lassen um einen Eindruck der HTML-Email zu bekommen:

```bash
python3 scripts/preview_email.py
```

**Beispiel-Ausgabe:**

> --- 
> ### 2 neue Job-Empfehlungen
>
> ---
>
> #### [Sachbearbeiter*in (w/m/d) IT-Verfahrensbetreuung Wahldatenbank und Fachverfahren](https://www.arbeitsagentur.de/jobsuche/)
> 🏢 **Amt für Statistik Berlin-Brandenburg**  
> 📍 Berlin
>
> > Sehr passgenau zu deinem Datenlabor-/Prototyping-Kontext im öffentlichen Dienst: Du betreust und entwickelst eine interne Wahldatenbank samt Schnittstellen/Tools weiter, bereitest Daten auf, testest Funktionalitäten und baust Import/Export-Prozesse (XML/CSV) sowie Skripte für Systemkommunikation. Tech-Stack ist modern und stark Open-Source-fähig (u.a. PostgreSQL/MySQL/MariaDB möglich, Linux, Git, Python/R/JS optional). Rolle ist fachlich-technisch, nicht Beratung, nicht Forschung, und ausdrücklich unbefristet in Berlin.
>
> [→ Zur Stellenanzeige](https://www.arbeitsagentur.de/jobsuche/)
>
> ---
>
> #### [IT-Systemadministrator/in (m/w/d) Archivsystem](https://www.arbeitsagentur.de/jobsuche/)
> 🏢 **DRV Berlin-Brandenburg**  
> 📍 Berlin (oder Frankfurt (Oder))
>
> > Öffentlicher Dienst, unbefristet, Standort Berlin möglich und stark technisch/hands-on: Linux-Server, Betrieb/Monitoring einer digitalen Archivlösung, Systemanalysen, Automatisierung/DevOps-Ansätze und 2nd-Level-Support. Passt gut, wenn du dich technisch weiterentwickeln willst (Linux, Monitoring, Automatisierung). Kein Beratungsfokus, keine Forschung.
>
> [→ Zur Stellenanzeige](https://www.arbeitsagentur.de/jobsuche/)
>
> ---
> 
> <sub>Automatisch generiert von Job Alert Agent</sub>
>
> ---

## Projektstruktur

- `scripts/main.py` - Haupt-Orchestrierer
- `scripts/config.py` - Zentrale Konfiguration und Pfade
- `scripts/jobsuche_api.py` - API-Abfrage bei der Bundesagentur für Arbeit
- `scripts/llm_agent.py` - KI-Verarbeitung (Shortlisting & Deep Dive)
- `scripts/past_job_suggestions.py` - Verwaltung bereits vorgeschlagener Jobs
- `scripts/report_generator.py` - Erstellung des generierten Berichts
- `scripts/report_template.html` - HTML-Berichtsvorlage
- `config/` - Ihre Konfigurationsdateien für das Suchprofil
- `data/` - Historie zur Deduplizierung
- `reports/` - Generierte Berichte

## Disclaimer / Nutzungsbedingungen

Bitte beachten Sie bei der Nutzung dieses Projekts die [Nutzungsbedingungen der Bundesagentur für Arbeit (BA)](https://www.arbeitsagentur.de/nutzungsbedingungen#2a-Nutzung-des-Portals%C2%A0). Insbesondere ist es nicht zulässig "bestehende Kommunikations- bzw. Programmierschnittstellen entgegen dem von der BA beabsichtigten Zweck zu verwenden". Außerdem sollten Aktivitäten, die "zu einer hohen Belastung der Infrastruktur führen können" unterlassen werden. Zusammengefasst sollte das Tool also im üblichen Rahmen, ausschließlich zur eigenen, privaten Stellensuche verwendet werden.
