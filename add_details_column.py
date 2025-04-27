from app import app, db
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

def add_details_column():
    """Add the details column to the Payment table if it doesn't exist"""
    
    with app.app_context():
        inspector = Inspector.from_engine(db.engine)
        columns = [column['name'] for column in inspector.get_columns('payment')]
        
        if 'details' not in columns:
            print("Adding 'details' column to Payment table...")
            
            # Use SQLAlchemy Core to add the column
            with db.engine.begin() as conn:
                conn.execute(sa.text("ALTER TABLE payment ADD COLUMN details TEXT"))
            
            print("Migration completed successfully!")
        else:
            print("Column 'details' already exists in Payment table.")

if __name__ == "__main__":
    add_details_column() 