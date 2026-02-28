#!/usr/bin/env python3
import os
import webbrowser

def generate_preview():
    # Dummy jobs
    dummy_jobs = [
        {
            'title': 'Senior Data Scientist (m/w/d)',
            'employer': 'Tech Corp Berlin',
            'location': 'Berlin (Mitte)',
            'refnr': '12345-67890-S',
            'reason': 'This perfectly matches your background in Python, Machine Learning and Data Analysis. It also offers a permanent contract and is right in your commuting radius.',
            'detail_url': 'https://www.arbeitsagentur.de/jobsuche/'
        },
        {
            'title': 'Machine Learning Engineer',
            'employer': 'AI Innovations GmbH',
            'location': 'Königs Wusterhausen',
            'refnr': '98765-43210-S',
            'reason': 'Great opportunity very close to home. The role focuses heavily on predictive modeling and deploying LLMs.',
            'detail_url': 'https://www.arbeitsagentur.de/jobsuche/'
        },
        {
            'title': 'Data Analyst - Public Sector',
            'employer': 'Bundesministerium',
            'location': 'Berlin',
            'refnr': '55555-44444-S',
            'reason': 'Matches your preference for public sector roles with a focus on data analysis and visualization. TV-L 14 salary band.',
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
