from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        conn.execute(text('ALTER TABLE vertical_chat ADD COLUMN query_text TEXT;'))
        print("✅ Column 'query_text' added successfully.")
