import click
from flask.cli import with_appcontext
from app.models import User
from app import db

@click.command('create-admin')
@click.option('--username', prompt=True, help='Admin username')
@click.option('--email', prompt=True, help='Admin email')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password')
@with_appcontext
def create_admin(username, email, password):
    """Create an admin user."""
    try:
        # Check if user already exists
        if User.query.filter_by(username=username).first() is not None:
            click.echo(f'User {username} already exists.')
            return
        
        if User.query.filter_by(email=email).first() is not None:
            click.echo(f'Email {email} is already registered.')
            return
        
        # Create new admin user
        user = User(username=username, email=email, is_admin=True)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        click.echo(f'Admin user {username} created successfully.')
    except Exception as e:
        click.echo(f'Error creating admin user: {str(e)}')


@click.command('seed-data')
@click.option('--confirm', is_flag=True, help='Confirm data seeding')
@with_appcontext
def seed_data(confirm):
    """Seed the database with initial data."""
    if not confirm:
        click.echo('Please use --confirm flag to confirm seeding the database.')
        return
    
    from app.models import Location
    from datetime import datetime
    import random
    
    # Check if we already have seed data
    if Location.query.count() > 0:
        click.echo('Database already contains locations. Skipping seed operation.')
        return
    
    try:
        # Get admin user for creating locations
        admin = User.query.filter_by(is_admin=True).first()
        
        if not admin:
            click.echo('No admin user found. Please create an admin user first with "flask create-admin"')
            return
        
        # Seed locations data
        locations = [
            {
                'name': 'Timisoara City Hall',
                'description': 'The city hall building with full accessibility features.',
                'lat': 45.756705,
                'lng': 21.231116,
                'address': 'Bulevardul C.D. Loga 1, Timișoara',
                'location_type': 'publicbuilding',
                'has_ramp': True,
                'has_accessible_wc': True,
                'has_accessible_parking': True,
                'has_accessible_entrance': True,
                'has_braille': False,
                'has_audio_guidance': False,
                'has_staff_assistance': True
            },
            {
                'name': 'Timisoara North Train Station',
                'description': 'Main train station with wheelchair access and assistance.',
                'lat': 45.752136,
                'lng': 21.218210,
                'address': 'Strada Gării 1, Timișoara',
                'location_type': 'transportation',
                'has_ramp': True,
                'has_accessible_wc': True,
                'has_accessible_parking': True,
                'has_accessible_entrance': True,
                'has_braille': False,
                'has_audio_guidance': True,
                'has_staff_assistance': True
            },
            {
                'name': 'Iulius Mall',
                'description': 'Shopping mall with full accessibility features.',
                'lat': 45.770080,
                'lng': 21.228149,
                'address': 'Strada Aristide Demetriade 1, Timișoara',
                'location_type': 'shop',
                'has_ramp': True,
                'has_accessible_wc': True,
                'has_accessible_parking': True,
                'has_accessible_entrance': True,
                'has_braille': True,
                'has_audio_guidance': False,
                'has_staff_assistance': True
            },
            {
                'name': 'Timisoara Orthodox Cathedral',
                'description': 'The main cathedral with ramp access for visitors.',
                'lat': 45.755131,
                'lng': 21.225734,
                'address': 'Bulevardul Regele Ferdinand I, Timișoara',
                'location_type': 'attraction',
                'has_ramp': True,
                'has_accessible_wc': False,
                'has_accessible_parking': False,
                'has_accessible_entrance': True,
                'has_braille': False,
                'has_audio_guidance': False,
                'has_staff_assistance': True
            },
            {
                'name': 'Timisoara County Hospital',
                'description': 'Main hospital with full accessibility.',
                'lat': 45.764080,
                'lng': 21.242149,
                'address': 'Bulevardul Liviu Rebreanu 156, Timișoara',
                'location_type': 'healthcare',
                'has_ramp': True,
                'has_accessible_wc': True,
                'has_accessible_parking': True,
                'has_accessible_entrance': True,
                'has_braille': True,
                'has_audio_guidance': True,
                'has_staff_assistance': True
            }
        ]
        
        for loc_data in locations:
            location = Location(
                name=loc_data['name'],
                description=loc_data['description'],
                lat=loc_data['lat'],
                lng=loc_data['lng'],
                address=loc_data['address'],
                location_type=loc_data['location_type'],
                has_ramp=loc_data['has_ramp'],
                has_accessible_wc=loc_data['has_accessible_wc'],
                has_accessible_parking=loc_data['has_accessible_parking'],
                has_accessible_entrance=loc_data['has_accessible_entrance'],
                has_braille=loc_data['has_braille'],
                has_audio_guidance=loc_data['has_audio_guidance'],
                has_staff_assistance=loc_data['has_staff_assistance'],
                user_id=admin.id,
                is_approved=True
            )
            db.session.add(location)
        
        db.session.commit()
        click.echo(f'Added {len(locations)} sample locations to the database.')
        
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error seeding database: {str(e)}')


def register_commands(app):
    """Register custom Flask commands."""
    app.cli.add_command(create_admin)
    app.cli.add_command(seed_data)
