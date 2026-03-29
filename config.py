import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-12345')
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', 'dev-enc-key-12345')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///campus_match.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEV_MODE = os.environ.get('DEV_MODE', 'true').lower() == 'true'
    DEV_ALLOW_ANY_EMAIL = DEV_MODE
    ALLOWED_EMAIL_DOMAIN = os.environ.get('ALLOWED_EMAIL_DOMAIN', 'stu.pku.edu.cn')

    CODE_EXPIRE_SECONDS = 300
    CODE_COOLDOWN_SECONDS = 60

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.163.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 465))
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME', '')

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'