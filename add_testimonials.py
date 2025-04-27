from app import create_app, db
from models import User, Testimonial
from datetime import datetime

app = create_app()

def add_sample_testimonials():
    with app.app_context():
        # Get some users to use as testimonial authors
        users = User.query.all()
        
        if not users:
            print("No users found in the database. Please create some users first.")
            return
        
        # Sample testimonials
        testimonials = [
            {
                "content": "This platform has completely transformed my learning experience. The courses are well-structured and the instructors are incredibly knowledgeable.",
                "rating": 5
            },
            {
                "content": "I've taken several courses here and each one has been excellent. The video quality is great and the content is always up-to-date.",
                "rating": 5
            },
            {
                "content": "The interactive quizzes and assignments really help reinforce the learning. I've learned more in a few weeks than I did in a semester of college!",
                "rating": 4
            },
            {
                "content": "The community aspect is fantastic. Being able to discuss topics with other students and get feedback from instructors has been invaluable.",
                "rating": 5
            },
            {
                "content": "The platform is easy to navigate and the mobile app works great. I can learn on the go, which fits perfectly with my busy schedule.",
                "rating": 4
            },
            {
                "content": "I was skeptical at first, but after completing my first course, I'm a believer. The certificate I received has already helped me land a new job!",
                "rating": 5
            }
        ]
        
        # Check if testimonials already exist
        existing_testimonials = Testimonial.query.count()
        if existing_testimonials > 0:
            print(f"Found {existing_testimonials} existing testimonials. Skipping creation.")
            return
        
        # Add testimonials
        for i, testimonial_data in enumerate(testimonials):
            # Cycle through users
            user = users[i % len(users)]
            
            testimonial = Testimonial(
                user_id=user.id,
                content=testimonial_data["content"],
                rating=testimonial_data["rating"],
                is_approved=True,
                created_at=datetime.utcnow()
            )
            
            db.session.add(testimonial)
        
        db.session.commit()
        print(f"Added {len(testimonials)} sample testimonials to the database.")

if __name__ == "__main__":
    add_sample_testimonials() 