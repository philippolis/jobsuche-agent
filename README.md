# Jobsuche Agent (Template)

KI-gestützte Jobsuche mit der `jobsuche-api` der Arbeitsagentur + OpenAI-Ranking.

Nutzen Sie dieses Repository als Ausgangspunkt für Ihren eigenen, personalisierten Job-Alert-Workflow.

## Was dieses Projekt macht

- Ruft aktuelle Stellenangebote über die API der Arbeitsagentur ab.
- Nutzt OpenAI, um basierend auf den Stellenbeschreibungen passende Jobs auszuwählen.
- Erstellt Markdown-Berichte im Ordner `reports/`.
- Verfolgt bereits vorgeschlagene Jobs im Ordner `data/`, um Duplikate zu vermeiden.

## 1) Erstellen Sie Ihr eigenes Repo aus diesem Template

1. Klicken Sie auf GitHub auf **Use this template**.
2. Erstellen Sie Ihr eigenes Repository.
3. Klonen Sie Ihr neues Repo lokal.

## 2) Lokale Einrichtung

Abhängigkeiten installieren:

```bash
pip install -r requirements.txt
```

Fügen Sie Ihren OpenAI-Schlüssel zur Datei `.env` hinzu:

```env
OPENAI_API_KEY=ihr_schluessel_hier
```

## 3) Personalisieren

Bearbeiten Sie diese Dateien:

- `config/candidate_profile.md` - Ihr Profil, Einschränkungen und Präferenzen
- `config/job_search_config.env` - Suchbegriffe, Ort, Umkreis, Aktualität

## 4) Ausführen

```bash
python3 scripts/generate_report.py
```

Ausgabe:

- `reports/job_report_<zeitstempel>.md`

## Nutzung mit GitHub Actions (optional)

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

## Projektstruktur

- `scripts/generate_report.py` - Haupt-Orchestrierer
- `scripts/fetch_jobsuche_jobs.py` - API-Abfrage + Anreicherung mit Stellenbeschreibungen
- `scripts/report_template.html` - HTML-Berichtsvorlage
- `config/` - Ihre Konfigurationsdateien für das Suchprofil
- `data/` - Historie zur Deduplizierung
- `reports/` - Generierte Berichte
