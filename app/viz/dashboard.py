import os

def render_dashboard():
    html_path = os.path.join(os.path.dirname(__file__), 'dashboard.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        return f.read()