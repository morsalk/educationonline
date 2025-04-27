from app import create_app
from migrations.add_category_level import upgrade

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        print("Running database migration to add category and level fields...")
        upgrade()
        print("Migration completed successfully!") 