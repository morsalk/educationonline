from app import create_app
from migrations.add_duration_days import upgrade

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        print("Running database migration...")
        upgrade()
        print("Migration completed successfully!") 