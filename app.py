"""
Simple Flask Web Application with TailwindCSS
=============================================
A minimal web app demonstrating Flask routes, templates,
and integration with TailwindCSS for styling.
"""

from flask import Flask, render_template, request, jsonify
import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')

# Sample data for demonstration
PROJECTS = [
    {
        'id': 1,
        'title': 'E-Commerce Platform',
        'description': 'A modern e-commerce solution with React and Python',
        'technologies': ['React', 'Python', 'Flask', 'PostgreSQL'],
        'image': 'https://placehold.co/600x400/2563eb/white?text=E-Commerce',
        'url': '#'
    },
    {
        'id': 2,
        'title': 'Task Management App',
        'description': 'Collaborative task management with real-time updates',
        'technologies': ['Vue.js', 'Node.js', 'MongoDB', 'WebSocket'],
        'image': 'https://placehold.co/600x400/7c3aed/white?text=Task+App',
        'url': '#'
    },
    {
        'id': 3,
        'title': 'Weather Dashboard',
        'description': 'Real-time weather tracking with interactive maps',
        'technologies': ['JavaScript', 'Python', 'OpenWeather API', 'D3.js'],
        'image': 'https://placehold.co/600x400/db2777/white?text=Weather',
        'url': '#'
    }
]

# Route for home page
@app.route('/')
def index():
    """Render the home page with all projects"""
    current_year = datetime.datetime.now().year
    return render_template(
        'index.html',
        projects=PROJECTS,
        current_year=current_year,
        page_title='Simple Python Web App'
    )

# Route for about page
@app.route('/about')
def about():
    """Render the about page"""
    return render_template(
        'index.html',
        page='about',
        current_year=datetime.datetime.now().year,
        page_title='About Us'
    )

# API endpoint to get projects (JSON)
@app.route('/api/projects')
def get_projects():
    """Return projects as JSON data"""
    return jsonify({
        'success': True,
        'data': PROJECTS,
        'count': len(PROJECTS)
    })

# API endpoint to get a single project
@app.route('/api/projects/<int:project_id>')
def get_project(project_id):
    """Return a single project by ID"""
    project = next((p for p in PROJECTS if p['id'] == project_id), None)
    if project:
        return jsonify({'success': True, 'data': project})
    return jsonify({'success': False, 'error': 'Project not found'}), 404

# Form handling example
@app.route('/contact', methods=['POST'])
def contact():
    """Handle contact form submission"""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        
        # Here you would typically send an email or save to database
        print(f"Contact form submission - Name: {name}, Email: {email}, Message: {message}")
        
        return jsonify({
            'success': True,
            'message': f'Thanks {name}! We\'ll get back to you soon.'
        })

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template(
        'index.html',
        page='404',
        current_year=datetime.datetime.now().year,
        page_title='Page Not Found'
    ), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Handle 500 errors"""
    return render_template(
        'index.html',
        page='500',
        current_year=datetime.datetime.now().year,
        page_title='Server Error'
    ), 500

# Run the application
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)