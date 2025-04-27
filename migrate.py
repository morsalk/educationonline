from app import app, db
from datetime import datetime
from sqlalchemy import text

def run_migration():
    with app.app_context():
        # Add the columns if they don't exist
        with db.engine.connect() as conn:
            try:
                # User table columns
                result = conn.execute(text("PRAGMA table_info(user)")).fetchall()
                columns = [row[1] for row in result]
                
                # Check if phone column exists
                if 'phone' not in columns:
                    print('Adding phone column...')
                    conn.execute(text('ALTER TABLE user ADD COLUMN phone VARCHAR(20)'))
                    conn.commit()
                else:
                    print('phone column already exists')
                
                # Check if bio column exists
                if 'bio' not in columns:
                    print('Adding bio column...')
                    conn.execute(text('ALTER TABLE user ADD COLUMN bio TEXT'))
                    conn.commit()
                else:
                    print('bio column already exists')
                
                # Check if profile_pic column exists
                if 'profile_pic' not in columns:
                    print('Adding profile_pic column...')
                    conn.execute(text("ALTER TABLE user ADD COLUMN profile_pic VARCHAR(200) DEFAULT 'default.jpg'"))
                    conn.commit()
                else:
                    print('profile_pic column already exists')
                
                # Check if is_approved column exists
                if 'is_approved' not in columns:
                    print('Adding is_approved column...')
                    conn.execute(text('ALTER TABLE user ADD COLUMN is_approved BOOLEAN DEFAULT FALSE'))
                    conn.commit()
                else:
                    print('is_approved column already exists')
                
                # Check if approval_date column exists
                if 'approval_date' not in columns:
                    print('Adding approval_date column...')
                    conn.execute(text('ALTER TABLE user ADD COLUMN approval_date TIMESTAMP'))
                    conn.commit()
                else:
                    print('approval_date column already exists')
                
                # Check if approved_by column exists
                if 'approved_by' not in columns:
                    print('Adding approved_by column...')
                    conn.execute(text('ALTER TABLE user ADD COLUMN approved_by INTEGER REFERENCES user(id)'))
                    conn.commit()
                else:
                    print('approved_by column already exists')
                
                # Course table columns
                result = conn.execute(text("PRAGMA table_info(course)")).fetchall()
                columns = [row[1] for row in result]
                
                if 'max_enrollments' not in columns:
                    print('Adding max_enrollments column...')
                    conn.execute(text('ALTER TABLE course ADD COLUMN max_enrollments INTEGER DEFAULT 100'))
                    conn.commit()
                else:
                    print('max_enrollments column already exists')
                
                if 'enrollment_deadline' not in columns:
                    print('Adding enrollment_deadline column...')
                    conn.execute(text('ALTER TABLE course ADD COLUMN enrollment_deadline TIMESTAMP'))
                    conn.commit()
                else:
                    print('enrollment_deadline column already exists')
                    
                # Enrollment table columns
                result = conn.execute(text("PRAGMA table_info(enrollment)")).fetchall()
                columns = [row[1] for row in result]
                
                if 'expires_at' not in columns:
                    print('Adding expires_at column...')
                    conn.execute(text('ALTER TABLE enrollment ADD COLUMN expires_at TIMESTAMP'))
                    conn.commit()
                else:
                    print('expires_at column already exists')
                    
                if 'subscription_type' not in columns:
                    print('Adding subscription_type column...')
                    conn.execute(text("ALTER TABLE enrollment ADD COLUMN subscription_type VARCHAR(20) DEFAULT 'unlimited'"))
                    conn.commit()
                else:
                    print('subscription_type column already exists')
                    
                if 'is_active' not in columns:
                    print('Adding is_active column...')
                    conn.execute(text('ALTER TABLE enrollment ADD COLUMN is_active BOOLEAN DEFAULT TRUE'))
                    conn.commit()
                else:
                    print('is_active column already exists')
                    
                if 'subscription_renewed' not in columns:
                    print('Adding subscription_renewed column...')
                    conn.execute(text('ALTER TABLE enrollment ADD COLUMN subscription_renewed TIMESTAMP'))
                    conn.commit()
                else:
                    print('subscription_renewed column already exists')

                print('Migration completed successfully!')
            except Exception as e:
                print(f'Error during migration: {str(e)}')
                # If tables don't exist, create them
                db.create_all()
                print('Created all tables from scratch')

if __name__ == "__main__":
    run_migration()