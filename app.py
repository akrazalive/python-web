"""
Project Management System
========================
A complete Flask application with user authentication, admin panel,
and project/portfolio management.
"""

import os
import secrets
from datetime import datetime
from PIL import Image
from flask import Flask, render_template, url_for, flash, redirect, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, FloatField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))

# Database configuration - AWS PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://username:password@host:5432/database')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload configuration
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# ============================================================================
# DATABASE MODELS
# ============================================================================

class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    projects = db.relationship('Project', backref='author', lazy=True)
    
    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

class Project(db.Model):
    """Project model for portfolio items"""
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    client = db.Column(db.String(200))
    completion_date = db.Column(db.Date)
    project_url = db.Column(db.String(500))
    image_file = db.Column(db.String(200), nullable=False, default='default.jpg')
    featured = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(50), default='active')  # active, completed, archived
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def __repr__(self):
        return f"Project('{self.title}', '{self.category}')"

class Portfolio(db.Model):
    """Portfolio settings and information"""
    __tablename__ = 'portfolio'
    
    id = db.Column(db.Integer, primary_key=True)
    site_title = db.Column(db.String(200), default='My Portfolio')
    site_description = db.Column(db.Text, default='Welcome to my portfolio')
    owner_name = db.Column(db.String(200))
    owner_title = db.Column(db.String(200))
    owner_bio = db.Column(db.Text)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    address = db.Column(db.String(300))
    github_url = db.Column(db.String(500))
    linkedin_url = db.Column(db.String(500))
    twitter_url = db.Column(db.String(500))
    theme_color = db.Column(db.String(50), default='blue')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Setting(db.Model):
    """System settings"""
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.String(500))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ============================================================================
# FORMS
# ============================================================================

class RegistrationForm(FlaskForm):
    """User registration form"""
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose another.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use another.')

class LoginForm(FlaskForm):
    """User login form"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class ProjectForm(FlaskForm):
    """Project creation/editing form"""
    title = StringField('Project Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[DataRequired()])
    category = SelectField('Category', choices=[
        ('web', 'Web Development'),
        ('mobile', 'Mobile App'),
        ('design', 'Design'),
        ('consulting', 'Consulting'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    client = StringField('Client Name', validators=[Length(max=200)])
    completion_date = StringField('Completion Date (YYYY-MM-DD)')
    project_url = StringField('Project URL', validators=[Length(max=500)])
    featured = BooleanField('Featured Project')
    status = SelectField('Status', choices=[
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('archived', 'Archived')
    ])
    submit = SubmitField('Save Project')

class PortfolioForm(FlaskForm):
    """Portfolio settings form"""
    site_title = StringField('Site Title', validators=[Length(max=200)])
    site_description = TextAreaField('Site Description')
    owner_name = StringField('Your Name', validators=[Length(max=200)])
    owner_title = StringField('Your Title/Profession', validators=[Length(max=200)])
    owner_bio = TextAreaField('Biography')
    email = StringField('Email', validators=[Email()])
    phone = StringField('Phone Number', validators=[Length(max=50)])
    address = StringField('Address', validators=[Length(max=300)])
    github_url = StringField('GitHub URL', validators=[Length(max=500)])
    linkedin_url = StringField('LinkedIn URL', validators=[Length(max=500)])
    twitter_url = StringField('Twitter URL', validators=[Length(max=500)])
    submit = SubmitField('Save Settings')

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def save_picture(form_picture):
    """Save uploaded picture with random name"""
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.config['UPLOAD_FOLDER'], picture_fn)
    
    # Resize image if needed
    output_size = (800, 600)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    
    return picture_fn

def init_settings():
    """Initialize default settings"""
    if not Portfolio.query.first():
        default_portfolio = Portfolio(
            site_title='My Portfolio',
            site_description='Welcome to my professional portfolio',
            theme_color='blue'
        )
        db.session.add(default_portfolio)
    
    if not Setting.query.filter_by(key='site_name').first():
        site_name = Setting(key='site_name', value='Project Manager', description='Site name')
        db.session.add(site_name)
    
    db.session.commit()

# ============================================================================
# ROUTES - PUBLIC PAGES
# ============================================================================

@app.route('/')
def index():
    """Home page"""
    portfolio = Portfolio.query.first()
    featured_projects = Project.query.filter_by(featured=True, status='active').limit(3).all()
    return render_template('index.html', 
                         title='Home',
                         portfolio=portfolio,
                         featured_projects=featured_projects)

@app.route('/projects')
def projects():
    """Public projects listing"""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', 'all')
    
    if category and category != 'all':
        projects = Project.query.filter_by(category=category, status='active').order_by(Project.created_at.desc()).paginate(page=page, per_page=6)
    else:
        projects = Project.query.filter_by(status='active').order_by(Project.created_at.desc()).paginate(page=page, per_page=6)
    
    categories = db.session.query(Project.category).distinct().all()
    return render_template('projects.html',
                         title='Projects',
                         projects=projects,
                         categories=categories,
                         current_category=category)


# ============================================================================
# ROUTES - AUTHENTICATION
# ============================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if this is the first user (make them admin)
        is_admin = User.query.count() == 0
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,  # In production, hash this!
            is_admin=is_admin
        )
        db.session.add(user)
        db.session.commit()
        
        flash(f'Account created for {form.username.data}! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        # Simple password check (in production, use hashed passwords)
        if user and user.password == form.password.data:
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# ============================================================================
# ROUTES - USER DASHBOARD
# ============================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    user_projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.created_at.desc()).all()
    return render_template('dashboard.html', 
                         title='Dashboard',
                         projects=user_projects)


@app.route('/project/<int:project_id>')
def project_detail(project_id):
    """Project detail page"""
    project = Project.query.get_or_404(project_id)
    # Get related projects (same category, excluding current)
    related_projects = Project.query.filter(
        Project.category == project.category,
        Project.id != project.id,
        Project.status == 'active'
    ).limit(3).all()
    return render_template('project_detail.html', 
                         title=project.title, 
                         project=project,
                         related_projects=related_projects)

@app.route('/dashboard/projects/new', methods=['GET', 'POST'])
@login_required
def new_project():
    """Create new project"""
    form = ProjectForm()
    
    if form.validate_on_submit():
        project = Project(
            title=form.title.data,
            description=form.description.data,
            category=form.category.data,
            client=form.client.data,
            project_url=form.project_url.data,
            featured=form.featured.data,
            status=form.status.data,
            user_id=current_user.id
        )

        # FIX: Handle completion date for new projects
        completion_date = request.form.get('completion_date')
        if completion_date:
            try:
                project.completion_date = datetime.strptime(completion_date, '%Y-%m-%d').date()
            except:
                project.completion_date = None
        
        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                picture_file = save_picture(file)
                project.image_file = picture_file
        
        db.session.add(project)
        db.session.commit()
        
        flash('Your project has been created!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('add_project.html', title='New Project', form=form)

@app.route('/dashboard/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    """Edit project"""
    project = Project.query.get_or_404(project_id)
    
    # Check permission
    if project.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    form = ProjectForm()
    
    if form.validate_on_submit():
        project.title = form.title.data
        project.description = form.description.data
        project.category = form.category.data
        project.client = form.client.data
        project.project_url = form.project_url.data
        project.featured = form.featured.data
        project.status = form.status.data

        completion_date = request.form.get('completion_date')
        if completion_date:
            try:
                project.completion_date = datetime.strptime(completion_date, '%Y-%m-%d').date()
            except:
                project.completion_date = None
        
        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                # Delete old image if not default
                if project.image_file != 'default.jpg':
                    old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], project.image_file)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                picture_file = save_picture(file)
                project.image_file = picture_file
        
        db.session.commit()
        flash('Project has been updated!', 'success')
        return redirect(url_for('dashboard'))
    
    # Pre-populate form
    elif request.method == 'GET':
        form.title.data = project.title
        form.description.data = project.description
        form.category.data = project.category
        form.client.data = project.client
        form.project_url.data = project.project_url
        form.featured.data = project.featured
        form.status.data = project.status
        form.completion_date.data = project.completion_date.strftime('%Y-%m-%d') if project.completion_date else ''

    print(f"Rendering edit_project.html with project: {project.title}")
    print(f"Template folder: {app.template_folder}")    
    
    return render_template('edit_project.html', title='Edit Project', form=form, project=project)

@app.route('/dashboard/projects/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    """Delete project"""
    project = Project.query.get_or_404(project_id)
    
    # Check permission
    if project.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    # Delete image file
    if project.image_file != 'default.jpg':
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], project.image_file)
        if os.path.exists(image_path):
            os.remove(image_path)
    
    db.session.delete(project)
    db.session.commit()
    
    flash('Project has been deleted!', 'success')
    return redirect(url_for('dashboard'))

# ============================================================================
# ROUTES - ADMIN PANEL
# ============================================================================

@app.route('/admin')
@login_required
def admin_dashboard():
    """Admin dashboard"""
    if not current_user.is_admin:
        abort(403)
    
    total_users = User.query.count()
    total_projects = Project.query.count()
    # Get all users for the admins count
    users = User.query.all()
    recent_projects = Project.query.order_by(Project.created_at.desc()).limit(5).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         title='Admin Dashboard',
                         total_users=total_users,
                         total_projects=total_projects,
                         users=users,  # Add this line
                         recent_projects=recent_projects,
                         recent_users=recent_users)

@app.route('/admin/projects')
@login_required
def admin_projects():
    """Admin project management"""
    if not current_user.is_admin:
        abort(403)
    
    page = request.args.get('page', 1, type=int)
    projects = Project.query.order_by(Project.created_at.desc()).paginate(page=page, per_page=10)
    return render_template('admin/projects.html', title='Manage Projects', projects=projects)

@app.route('/admin/portfolio', methods=['GET', 'POST'])
@login_required
def admin_portfolio():
    """Portfolio settings"""
    if not current_user.is_admin:
        abort(403)
    
    portfolio = Portfolio.query.first()
    if not portfolio:
        portfolio = Portfolio()
        db.session.add(portfolio)
        db.session.commit()
    
    form = PortfolioForm()
    
    if form.validate_on_submit():
        portfolio.site_title = form.site_title.data
        portfolio.site_description = form.site_description.data
        portfolio.owner_name = form.owner_name.data
        portfolio.owner_title = form.owner_title.data
        portfolio.owner_bio = form.owner_bio.data
        portfolio.email = form.email.data
        portfolio.phone = form.phone.data
        portfolio.address = form.address.data
        portfolio.github_url = form.github_url.data
        portfolio.linkedin_url = form.linkedin_url.data
        portfolio.twitter_url = form.twitter_url.data
        
        db.session.commit()
        flash('Portfolio settings updated!', 'success')
        return redirect(url_for('admin_portfolio'))
    
    elif request.method == 'GET':
        form.site_title.data = portfolio.site_title
        form.site_description.data = portfolio.site_description
        form.owner_name.data = portfolio.owner_name
        form.owner_title.data = portfolio.owner_title
        form.owner_bio.data = portfolio.owner_bio
        form.email.data = portfolio.email
        form.phone.data = portfolio.phone
        form.address.data = portfolio.address
        form.github_url.data = portfolio.github_url
        form.linkedin_url.data = portfolio.linkedin_url
        form.twitter_url.data = portfolio.twitter_url
    
    return render_template('admin/portfolio.html', title='Portfolio Settings', form=form)

@app.route('/admin/settings')
@login_required
def admin_settings():
    """System settings"""
    if not current_user.is_admin:
        abort(403)
    
    settings = Setting.query.all()
    return render_template('admin/settings.html', title='System Settings', settings=settings)

@app.route('/admin/users')
@login_required
def admin_users():
    """User management"""
    if not current_user.is_admin:
        abort(403)
    
    users = User.query.all()
    return render_template('admin/users.html', title='Manage Users', users=users)

@app.route('/admin/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
def toggle_admin(user_id):
    """Toggle user admin status"""
    if not current_user.is_admin:
        abort(403)
    
    user = User.query.get_or_404(user_id)
    
    # Don't let admin remove their own admin status
    if user.id == current_user.id:
        flash('You cannot change your own admin status!', 'warning')
    else:
        user.is_admin = not user.is_admin
        db.session.commit()
        flash(f'Admin status for {user.username} has been updated!', 'success')
    
    return redirect(url_for('admin_users'))

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

@app.cli.command("init-db")
def init_db_command():
    """Initialize the database with tables and default data"""
    db.create_all()
    init_settings()
    print("Database initialized successfully!")

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_settings()
    app.run(debug=True, host='0.0.0.0', port=5000)