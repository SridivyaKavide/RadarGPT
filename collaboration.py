from flask import jsonify, request
from flask_login import current_user
import json
from datetime import datetime

class CollaborationManager:
    """Manages team collaboration features"""
    
    def __init__(self, db):
        self.db = db
        
    def setup_models(self):
        """Set up database models for collaboration"""
        db = self.db
        
        class Team(db.Model):
            id = db.Column(db.Integer, primary_key=True)
            name = db.Column(db.String(100), nullable=False)
            created_at = db.Column(db.DateTime, default=datetime.utcnow)
            created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
            members = db.relationship('TeamMember', backref='team', lazy=True, cascade="all, delete-orphan")
            
        class TeamMember(db.Model):
            id = db.Column(db.Integer, primary_key=True)
            team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
            user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
            role = db.Column(db.String(20), default='member')  # 'admin' or 'member'
            joined_at = db.Column(db.DateTime, default=datetime.utcnow)
            
        class SharedQuery(db.Model):
            id = db.Column(db.Integer, primary_key=True)
            query_id = db.Column(db.Integer, db.ForeignKey('search_query.id'), nullable=False)
            team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
            shared_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
            shared_at = db.Column(db.DateTime, default=datetime.utcnow)
            
        class Comment(db.Model):
            id = db.Column(db.Integer, primary_key=True)
            query_id = db.Column(db.Integer, db.ForeignKey('search_query.id'), nullable=False)
            user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
            text = db.Column(db.Text, nullable=False)
            created_at = db.Column(db.DateTime, default=datetime.utcnow)
            
        # Add relationships to User model
        if hasattr(db.Model, 'User'):
            User = db.Model.User
            User.teams = db.relationship('TeamMember', backref='user', lazy=True)
            User.shared_queries = db.relationship('SharedQuery', 
                                                 primaryjoin="User.id == SharedQuery.shared_by",
                                                 backref='shared_by_user', lazy=True)
            User.comments = db.relationship('Comment', backref='user', lazy=True)
        
        return {
            'Team': Team,
            'TeamMember': TeamMember,
            'SharedQuery': SharedQuery,
            'Comment': Comment
        }
    
    def create_team(self, name):
        """Create a new team"""
        if not current_user.is_authenticated:
            return {"error": "Authentication required"}, 401
            
        Team = self.db.Model.Team
        TeamMember = self.db.Model.TeamMember
        
        # Create team
        team = Team(name=name, created_by=current_user.id)
        self.db.session.add(team)
        self.db.session.flush()  # Get team ID
        
        # Add creator as admin
        member = TeamMember(team_id=team.id, user_id=current_user.id, role='admin')
        self.db.session.add(member)
        self.db.session.commit()
        
        return {"success": True, "team_id": team.id, "name": team.name}, 201
    
    def add_team_member(self, team_id, username):
        """Add a member to a team"""
        if not current_user.is_authenticated:
            return {"error": "Authentication required"}, 401
            
        Team = self.db.Model.Team
        TeamMember = self.db.Model.TeamMember
        User = self.db.Model.User
        
        # Check if team exists and user is admin
        team = Team.query.get(team_id)
        if not team:
            return {"error": "Team not found"}, 404
            
        # Check if user is admin
        is_admin = TeamMember.query.filter_by(
            team_id=team_id, 
            user_id=current_user.id,
            role='admin'
        ).first()
        
        if not is_admin:
            return {"error": "Permission denied"}, 403
            
        # Find user to add
        user = User.query.filter_by(username=username).first()
        if not user:
            return {"error": "User not found"}, 404
            
        # Check if already a member
        existing = TeamMember.query.filter_by(team_id=team_id, user_id=user.id).first()
        if existing:
            return {"error": "User is already a team member"}, 400
            
        # Add member
        member = TeamMember(team_id=team_id, user_id=user.id, role='member')
        self.db.session.add(member)
        self.db.session.commit()
        
        return {"success": True, "username": username}, 201
    
    def share_query(self, query_id, team_id):
        """Share a query with a team"""
        if not current_user.is_authenticated:
            return {"error": "Authentication required"}, 401
            
        SearchQuery = self.db.Model.SearchQuery
        SharedQuery = self.db.Model.SharedQuery
        TeamMember = self.db.Model.TeamMember
        
        # Check if query exists and belongs to user
        query = SearchQuery.query.get(query_id)
        if not query or query.user_id != current_user.id:
            return {"error": "Query not found or not owned by you"}, 404
            
        # Check if user is team member
        is_member = TeamMember.query.filter_by(
            team_id=team_id, 
            user_id=current_user.id
        ).first()
        
        if not is_member:
            return {"error": "You are not a member of this team"}, 403
            
        # Check if already shared
        existing = SharedQuery.query.filter_by(query_id=query_id, team_id=team_id).first()
        if existing:
            return {"error": "Query already shared with this team"}, 400
            
        # Share query
        shared = SharedQuery(
            query_id=query_id,
            team_id=team_id,
            shared_by=current_user.id
        )
        self.db.session.add(shared)
        self.db.session.commit()
        
        return {"success": True, "query_id": query_id, "team_id": team_id}, 201
    
    def add_comment(self, query_id, text):
        """Add a comment to a query"""
        if not current_user.is_authenticated:
            return {"error": "Authentication required"}, 401
            
        SearchQuery = self.db.Model.SearchQuery
        SharedQuery = self.db.Model.SharedQuery
        TeamMember = self.db.Model.TeamMember
        Comment = self.db.Model.Comment
        
        # Check if query exists
        query = SearchQuery.query.get(query_id)
        if not query:
            return {"error": "Query not found"}, 404
            
        # Check if user owns query or it's shared with them
        if query.user_id != current_user.id:
            # Check if query is shared with any team the user is in
            user_teams = TeamMember.query.filter_by(user_id=current_user.id).with_entities(TeamMember.team_id).all()
            user_team_ids = [t.team_id for t in user_teams]
            
            shared = SharedQuery.query.filter(
                SharedQuery.query_id == query_id,
                SharedQuery.team_id.in_(user_team_ids)
            ).first()
            
            if not shared:
                return {"error": "Permission denied"}, 403
        
        # Add comment
        comment = Comment(
            query_id=query_id,
            user_id=current_user.id,
            text=text
        )
        self.db.session.add(comment)
        self.db.session.commit()
        
        return {
            "success": True, 
            "comment_id": comment.id,
            "text": text,
            "username": current_user.username,
            "created_at": comment.created_at.isoformat()
        }, 201
    
    def get_comments(self, query_id):
        """Get all comments for a query"""
        if not current_user.is_authenticated:
            return {"error": "Authentication required"}, 401
            
        SearchQuery = self.db.Model.SearchQuery
        SharedQuery = self.db.Model.SharedQuery
        TeamMember = self.db.Model.TeamMember
        Comment = self.db.Model.Comment
        User = self.db.Model.User
        
        # Check if query exists
        query = SearchQuery.query.get(query_id)
        if not query:
            return {"error": "Query not found"}, 404
            
        # Check if user owns query or it's shared with them
        has_access = False
        if query.user_id == current_user.id:
            has_access = True
        else:
            # Check if query is shared with any team the user is in
            user_teams = TeamMember.query.filter_by(user_id=current_user.id).with_entities(TeamMember.team_id).all()
            user_team_ids = [t.team_id for t in user_teams]
            
            shared = SharedQuery.query.filter(
                SharedQuery.query_id == query_id,
                SharedQuery.team_id.in_(user_team_ids)
            ).first()
            
            if shared:
                has_access = True
        
        if not has_access:
            return {"error": "Permission denied"}, 403
        
        # Get comments with user info
        comments = self.db.session.query(
            Comment, User.username
        ).join(
            User, Comment.user_id == User.id
        ).filter(
            Comment.query_id == query_id
        ).order_by(
            Comment.created_at
        ).all()
        
        results = []
        for comment, username in comments:
            results.append({
                "id": comment.id,
                "text": comment.text,
                "username": username,
                "created_at": comment.created_at.isoformat()
            })
        
        return {"comments": results}, 200