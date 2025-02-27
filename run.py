from app import create_app
from app.config import admin_mode_switch

app = create_app()

if __name__ == '__main__':
    debug = admin_mode_switch

    app.run(debug=debug)

