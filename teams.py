from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import text

class TeamManager:
    def __init__(self, db):
        self.db = db
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """Ensure the teams-related tables exist"""
        with self.db.engine.connect() as conn:
            # Check if teams table exists
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='team'"))
            if not result.fetchone():
                # Create teams table
                conn.execute(text("""
                CREATE TABLE team (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES user(id)
                )
                """))
                
                # Create team_member table
                conn.execute(text("""
                CREATE TABLE team_member (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    role TEXT DEFAULT 'member',
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (team_id) REFERENCES team(id),
                    FOREIGN KEY (user_id) REFERENCES user(id),
                    UNIQUE(team_id, user_id)
                )
                """))
                
                # Create invitation table
                conn.execute(text("""
                CREATE TABLE invitation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id INTEGER NOT NULL,
                    email TEXT NOT NULL,
                    invited_by INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (team_id) REFERENCES team(id),
                    FOREIGN KEY (invited_by) REFERENCES user(id),
                    UNIQUE(team_id, email)
                )
                """))
                
                conn.commit()
    
    def create_team(self, name, description, user_id, members=None):
        """Create a new team"""
        try:
            # Insert team
            result = self.db.session.execute(
                text("""
                INSERT INTO team (name, description, created_by)
                VALUES (:name, :description, :user_id)
                RETURNING id
                """),
                {"name": name, "description": description, "user_id": user_id}
            )
            team_id = result.fetchone()[0]
            
            # Add creator as admin
            self.db.session.execute(
                text("""
                INSERT INTO team_member (team_id, user_id, role)
                VALUES (:team_id, :user_id, 'admin')
                """),
                {"team_id": team_id, "user_id": user_id}
            )
            
            # Add members as invitations
            if members:
                for email in members:
                    self.db.session.execute(
                        text("""
                        INSERT INTO invitation (team_id, email, invited_by)
                        VALUES (:team_id, :email, :user_id)
                        """),
                        {"team_id": team_id, "email": email, "user_id": user_id}
                    )
            
            self.db.session.commit()
            return {"id": team_id, "name": name}
        except Exception as e:
            self.db.session.rollback()
            raise e
    
    def get_user_teams(self, user_id):
        """Get teams that the user is a member of"""
        result = self.db.session.execute(
            text("""
            SELECT t.id, t.name, t.description, t.created_at,
                   COUNT(tm.id) as member_count,
                   MAX(CASE WHEN tm.user_id = :user_id THEN tm.role ELSE NULL END) as user_role
            FROM team t
            JOIN team_member tm ON t.id = tm.team_id
            WHERE t.id IN (SELECT team_id FROM team_member WHERE user_id = :user_id)
            GROUP BY t.id
            ORDER BY t.created_at DESC
            """),
            {"user_id": user_id}
        )
        
        teams = []
        for row in result:
            teams.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "created_at": row[3],
                "member_count": row[4],
                "user_role": row[5]
            })
        
        return teams
    
    def get_user_invitations(self, user_id):
        """Get pending invitations for a user"""
        # First get user email
        user_result = self.db.session.execute(
            text("SELECT username FROM user WHERE id = :user_id"),
            {"user_id": user_id}
        )
        user_row = user_result.fetchone()
        if not user_row:
            return []
        
        user_email = user_row[0]  # Using username as email for simplicity
        
        # Get invitations
        result = self.db.session.execute(
            text("""
            SELECT i.id, i.team_id, t.name as team_name, t.description as team_description,
                   u.username as invited_by, i.created_at
            FROM invitation i
            JOIN team t ON i.team_id = t.id
            JOIN user u ON i.invited_by = u.id
            WHERE i.email = :email AND i.status = 'pending'
            ORDER BY i.created_at DESC
            """),
            {"email": user_email}
        )
        
        invitations = []
        for row in result:
            invitations.append({
                "id": row[0],
                "team_id": row[1],
                "team_name": row[2],
                "team_description": row[3],
                "invited_by": row[4],
                "created_at": row[5]
            })
        
        return invitations
    
    def respond_to_invitation(self, invitation_id, user_id, action):
        """Accept or decline an invitation"""
        try:
            # Get invitation details
            result = self.db.session.execute(
                text("""
                SELECT i.team_id, i.email
                FROM invitation i
                JOIN user u ON i.email = u.username
                WHERE i.id = :invitation_id AND u.id = :user_id AND i.status = 'pending'
                """),
                {"invitation_id": invitation_id, "user_id": user_id}
            )
            
            row = result.fetchone()
            if not row:
                return {"error": "Invitation not found or already processed"}
            
            team_id = row[0]
            
            if action == 'accept':
                # Add user to team
                self.db.session.execute(
                    text("""
                    INSERT INTO team_member (team_id, user_id, role)
                    VALUES (:team_id, :user_id, 'member')
                    """),
                    {"team_id": team_id, "user_id": user_id}
                )
                
                # Update invitation status
                self.db.session.execute(
                    text("""
                    UPDATE invitation
                    SET status = 'accepted'
                    WHERE id = :invitation_id
                    """),
                    {"invitation_id": invitation_id}
                )
            else:
                # Update invitation status
                self.db.session.execute(
                    text("""
                    UPDATE invitation
                    SET status = 'declined'
                    WHERE id = :invitation_id
                    """),
                    {"invitation_id": invitation_id}
                )
            
            self.db.session.commit()
            return {"success": True, "action": action}
        except Exception as e:
            self.db.session.rollback()
            raise e
            
    def invite_members(self, team_id, user_id, emails):
        """Invite members to a team"""
        try:
            # Check if user is admin of the team
            result = self.db.session.execute(
                text("""
                SELECT role
                FROM team_member
                WHERE team_id = :team_id AND user_id = :user_id
                """),
                {"team_id": team_id, "user_id": user_id}
            )
            
            row = result.fetchone()
            if not row or row[0] != 'admin':
                return {"error": "You don't have permission to invite members"}
            
            # Add invitations
            for email in emails:
                try:
                    self.db.session.execute(
                        text("""
                        INSERT INTO invitation (team_id, email, invited_by)
                        VALUES (:team_id, :email, :user_id)
                        """),
                        {"team_id": team_id, "email": email, "user_id": user_id}
                    )
                except Exception as e:
                    # Skip duplicates
                    pass
            
            self.db.session.commit()
            return {"success": True, "invited": len(emails)}
        except Exception as e:
            self.db.session.rollback()
            raise e
            
    def cancel_invitation(self, invitation_id, user_id):
        """Cancel a pending invitation"""
        try:
            # Check if user is admin of the team
            result = self.db.session.execute(
                text("""
                SELECT i.team_id
                FROM invitation i
                JOIN team_member tm ON i.team_id = tm.team_id
                WHERE i.id = :invitation_id AND tm.user_id = :user_id AND tm.role = 'admin'
                """),
                {"invitation_id": invitation_id, "user_id": user_id}
            )
            
            row = result.fetchone()
            if not row:
                return {"error": "You don't have permission to cancel this invitation"}
            
            # Delete invitation
            self.db.session.execute(
                text("""
                DELETE FROM invitation
                WHERE id = :invitation_id
                """),
                {"invitation_id": invitation_id}
            )
            
            self.db.session.commit()
            return {"success": True}
        except Exception as e:
            self.db.session.rollback()
            raise e
    
    def get_team_details(self, team_id, user_id):
        """Get detailed information about a team"""
        # Check if user is a member of the team
        member_result = self.db.session.execute(
            text("""
            SELECT role
            FROM team_member
            WHERE team_id = :team_id AND user_id = :user_id
            """),
            {"team_id": team_id, "user_id": user_id}
        )
        
        member_row = member_result.fetchone()
        if not member_row:
            return {"error": "You are not a member of this team"}
        
        user_role = member_row[0]
        
        # Get team details
        team_result = self.db.session.execute(
            text("""
            SELECT t.id, t.name, t.description, t.created_at, u.username as created_by
            FROM team t
            JOIN user u ON t.created_by = u.id
            WHERE t.id = :team_id
            """),
            {"team_id": team_id}
        )
        
        team_row = team_result.fetchone()
        if not team_row:
            return {"error": "Team not found"}
        
        team = {
            "id": team_row[0],
            "name": team_row[1],
            "description": team_row[2],
            "created_at": team_row[3],
            "created_by": team_row[4],
            "user_role": user_role
        }
        
        # Get team members
        members_result = self.db.session.execute(
            text("""
            SELECT u.id, u.username, tm.role, tm.joined_at
            FROM team_member tm
            JOIN user u ON tm.user_id = u.id
            WHERE tm.team_id = :team_id
            ORDER BY tm.role = 'admin' DESC, tm.joined_at ASC
            """),
            {"team_id": team_id}
        )
        
        members = []
        for row in members_result:
            members.append({
                "id": row[0],
                "username": row[1],
                "role": row[2],
                "joined_at": row[3]
            })
        
        team["members"] = members
        
        # Get pending invitations if user is admin
        if user_role == 'admin':
            invitations_result = self.db.session.execute(
                text("""
                SELECT i.id, i.email, i.status, i.created_at, u.username as invited_by
                FROM invitation i
                JOIN user u ON i.invited_by = u.id
                WHERE i.team_id = :team_id AND i.status = 'pending'
                ORDER BY i.created_at DESC
                """),
                {"team_id": team_id}
            )
            
            invitations = []
            for row in invitations_result:
                invitations.append({
                    "id": row[0],
                    "email": row[1],
                    "status": row[2],
                    "created_at": row[3],
                    "invited_by": row[4]
                })
            
            team["invitations"] = invitations
        
        return team