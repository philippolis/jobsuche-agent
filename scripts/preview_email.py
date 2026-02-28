#!/usr/bin/env python3
import os
import webbrowser

def generate_preview():
    # Dummy jobs
    dummy_jobs = [
        {
            'title': 'Sachbearbeiter*in (w/m/d) IT-Verfahrensbetreuung Wahldatenbank und Fachverfahren',
            'employer': 'Amt für Statistik Berlin-Brandenburg',
            'location': 'Berlin',
            'refnr': '12345-67890-S',
            'reason': 'Sehr passgenau zu deinem Datenlabor-/Prototyping-Kontext im öffentlichen Dienst: Du betreust und entwickelst eine interne Wahldatenbank samt Schnittstellen/Tools weiter, bereitest Daten auf, testest Funktionalitäten und baust Import/Export-Prozesse (XML/CSV) sowie Skripte für Systemkommunikation. Tech-Stack ist modern und stark Open-Source-fähig (u.a. PostgreSQL/MySQL/MariaDB möglich, Linux, Git, Python/R/JS optional). Rolle ist fachlich-technisch, nicht Beratung, nicht Forschung, und ausdrücklich unbefristet in Berlin.',
            'detail_url': 'https://www.arbeitsagentur.de/jobsuche/'
        },
        {
            'title': 'IT-Systemadministrator/in (m/w/d) Archivsystem',
            'employer': 'DRV Berlin-Brandenburg',
            'location': 'Berlin (oder Frankfurt (Oder))',
            'refnr': '98765-43210-S',
            'reason': 'Öffentlicher Dienst, unbefristet, Standort Berlin möglich und stark technisch/hands-on: Linux-Server, Betrieb/Monitoring einer digitalen Archivlösung, Systemanalysen, Automatisierung/DevOps-Ansätze und 2nd-Level-Support. Passt gut, wenn du dich technisch weiterentwickeln willst (Linux, Monitoring, Automatisierung). Kein Beratungsfokus, keine Forschung.',
            'detail_url': 'https://www.arbeitsagentur.de/jobsuche/'
        }
    ]

    jobs_html_blocks = []
    for job in dummy_jobs:
        # Exact same HTML structure as in generate_report.py
        jobs_html_blocks.append(f"""
        <div class="job-item">
            <h2 class="job-title"><a href="{job['detail_url']}">{job['title']}</a></h2>
            <div class="job-meta">
                <div>🏢 <b>{job['employer']}</b></div>
                <div>📍 {job['location']}</div>
            </div>
            <div class="reason-text">
                {job['reason']}
            </div>
            <div class="action-link">
                <a href="{job['detail_url']}">→ Zur Stellenanzeige</a>
            </div>
        </div>
        """)

    # Read the HTML Template
    template_path = os.path.join(os.path.dirname(__file__), "report_template.html")
    with open(template_path, "r", encoding="utf-8") as tf:
        html_template = tf.read()

    # Fill template
    html_content = html_template.replace("{job_count}", str(len(dummy_jobs)))
    html_content = html_content.replace("{jobs_html}", "\n".join(jobs_html_blocks))

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
