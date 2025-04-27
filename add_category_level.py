from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        print("Adding category and level columns to Course table...")
        
        # Add category column
        db.session.execute(text("ALTER TABLE course ADD COLUMN category VARCHAR(50)"))
        
        # Add level column
        db.session.execute(text("ALTER TABLE course ADD COLUMN level VARCHAR(20)"))
        
        # Commit the changes
        db.session.commit()
        
        print("Columns added successfully!") 