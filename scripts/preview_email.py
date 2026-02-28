#!/usr/bin/env python3
import os
import webbrowser
from pathlib import Path

try:
    from report_generator import generate_html
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from report_generator import generate_html

def generate_preview():
    """Generate an HTML preview using dummy job data and open it in the default browser."""
    # Dummy jobs
    dummy_jobs = [
        {
            "title": "Sachbearbeiter*in (w/m/d) IT-Verfahrensbetreuung Wahldatenbank und Fachverfahren",
            "employer": "Amt für Statistik Berlin-Brandenburg",
            "location": "Berlin",
            "reason": "Sehr passgenau zu deinem Datenlabor-/Prototyping-Kontext im öffentlichen Dienst: Du betreust und entwickelst eine interne Wahldatenbank samt Schnittstellen/Tools weiter, bereitest Daten auf, testest Funktionalitäten und baust Import/Export-Prozesse (XML/CSV) sowie Skripte für Systemkommunikation. Tech-Stack ist modern und stark Open-Source-fähig (u.a. PostgreSQL/MySQL/MariaDB möglich, Linux, Git, Python/R/JS optional). Rolle ist fachlich-technisch, nicht Beratung, nicht Forschung, und ausdrücklich unbefristet in Berlin.",
            "detail_url": "https://www.arbeitsagentur.de/jobsuche/",
        },
        {
            "title": "IT-Systemadministrator/in (m/w/d) Archivsystem",
            "employer": "DRV Berlin-Brandenburg",
            "location": "Berlin (oder Frankfurt (Oder))",
            "reason": "Öffentlicher Dienst, unbefristet, Standort Berlin möglich und stark technisch/hands-on: Linux-Server, Betrieb/Monitoring einer digitalen Archivlösung, Systemanalysen, Automatisierung/DevOps-Ansätze und 2nd-Level-Support. Passt gut, wenn du dich technisch weiterentwickeln willst (Linux, Monitoring, Automatisierung). Kein Beratungsfokus, keine Forschung.",
            "detail_url": "https://www.arbeitsagentur.de/jobsuche/",
        },
    ]

    # Read the HTML Template
    template_path = Path(os.path.join(os.path.dirname(__file__), "report_template.html"))
    html_content = generate_html(dummy_jobs, template_path)

    # Save to preview.html
    preview_path = os.path.join(os.path.dirname(__file__), "preview.html")
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Generated preview at: {preview_path}")

    # Try to open in browser automatically
    try:
        file_url = f"file://{os.path.abspath(preview_path)}"
        webbrowser.open(file_url)
        print("Opened preview in your default browser.")
    except Exception as e:
        print(f"Could not open browser automatically: {e}")


if __name__ == "__main__":
    generate_preview()
