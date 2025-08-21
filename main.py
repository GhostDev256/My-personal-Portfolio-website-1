import sqlalchemy as sa
import sqlalchemy.orm as so
from app import application, db
from app.models import User

if __name__ == "__main__":
    application.run(host="0.0.0.0", port=80, debug=False)

@application.shell_context_processor
def make_shell_context():
    return {'sa': sa, 'so': so, 'db': db, 'User': User}