from APP import db, app

with app.app_context():
    db.create_all()
    print("All tables including 'contracts' have been created or checked in the database.")