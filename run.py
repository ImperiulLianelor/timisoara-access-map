from app import create_app
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get configuration from environment
config_name = os.environ.get('FLASK_ENV', 'development')
config_mapping = {
    'development': 'config.DevelopmentConfig',
    'testing': 'config.TestingConfig',
    'production': 'config.ProductionConfig'
}

app = create_app(config_mapping.get(config_name, 'config.DevelopmentConfig'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
