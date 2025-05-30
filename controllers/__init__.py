from .admin import admin_bp
from .user import user_bp

def register_controllers(app):
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)
