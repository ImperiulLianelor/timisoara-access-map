from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from flask_babel import gettext as _
from werkzeug.urls import url_parse
from app import db, limiter
from app.models import User
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, EmailField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

auth = Blueprint('auth', __name__)


class LoginForm(FlaskForm):
    username = StringField(_('Username'), validators=[DataRequired()])
    password = PasswordField(_('Password'), validators=[DataRequired()])
    remember_me = BooleanField(_('Remember Me'))
    submit = SubmitField(_('Sign In'))


class RegistrationForm(FlaskForm):
    username = StringField(_('Username'), validators=[DataRequired(), Length(min=4, max=64)])
    email = EmailField(_('Email'), validators=[DataRequired(), Email()])
    password = PasswordField(_('Password'), validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField(
        _('Repeat Password'), validators=[DataRequired(), EqualTo('password')])
    
    # Accessibility preferences
    needs_wheelchair = BooleanField(_('I use a wheelchair'))
    needs_visual_assistance = BooleanField(_('I need visual assistance'))
    needs_hearing_assistance = BooleanField(_('I need hearing assistance'))
    needs_cognitive_assistance = BooleanField(_('I need cognitive assistance'))
    
    submit = SubmitField(_('Register'))

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError(_('Please use a different username.'))

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError(_('Please use a different email address.'))


@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit("10/minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user is None or not user.check_password(form.password.data):
            flash(_('Invalid username or password'), 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash(_('This account has been deactivated. Please contact an administrator.'), 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        
        # Set user's preferred language
        session['language'] = user.preferred_language
        
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        
        flash(_('Login successful!'), 'success')
        return redirect(next_page)
    
    return render_template('auth/login.html', title=_('Sign In'), form=form)


@auth.route('/logout')
def logout():
    logout_user()
    flash(_('You have been logged out.'), 'info')
    return redirect(url_for('main.index'))


@auth.route('/register', methods=['GET', 'POST'])
@limiter.limit("5/hour")
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            needs_wheelchair=form.needs_wheelchair.data,
            needs_visual_assistance=form.needs_visual_assistance.data,
            needs_hearing_assistance=form.needs_hearing_assistance.data,
            needs_cognitive_assistance=form.needs_cognitive_assistance.data,
            preferred_language=session.get('language', 'ro')
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash(_('Registration successful! You can now log in.'), 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', title=_('Register'), form=form)


@auth.route('/language/<language>')
def set_language(language):
    # Validate that the language is supported
    if language not in ['en', 'ro']:
        language = 'ro'  # Default to Romanian
    
    session['language'] = language
    
    # If user is logged in, update their preference
    if current_user.is_authenticated:
        current_user.preferred_language = language
        db.session.commit()
    
    # Redirect back to the page they were on
    return redirect(request.referrer or url_for('main.index'))
