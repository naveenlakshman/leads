# models.py
from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ---------------------------
# User Model (Login accounts)
# ---------------------------
class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    # login identity
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=True)

    # auth
    password_hash = db.Column(db.String(255), nullable=False)

    # role control: "admin" (Naveen) or "counselor" (Chaithra)
    role = db.Column(db.String(20), nullable=False, default="counselor")

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # helpers
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"


# ---------------------------
# Lead Model (Main CRM data)
# ---------------------------
class Lead(db.Model):
    __tablename__ = "leads"

    id = db.Column(db.Integer, primary_key=True)

    # Basic details
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False, index=True)
    whatsapp = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.String(20), nullable=True)  # Male/Female/Other
    age = db.Column(db.Integer, nullable=True)

    # Education/background
    education_status = db.Column(db.String(50), nullable=True)  # PUC/Degree/Working/Job seeker etc.
    stream = db.Column(db.String(50), nullable=True)            # Commerce/Science/Arts/Other
    institute_name = db.Column(db.String(150), nullable=True)   # school/college/company

    # Interest & intent
    career_goal = db.Column(db.String(80), nullable=True)        # Job/Skill/Internship/Business etc.
    interested_courses = db.Column(db.String(255), nullable=True) # store as comma-separated for v1

    # Marketing
    lead_source = db.Column(db.String(80), nullable=True)        # Walk-in/Instagram/Referral etc.

    # Readiness
    start_timeframe = db.Column(db.String(30), nullable=True)    # Immediately/1 week/1 month/Exploring
    lead_score = db.Column(db.Integer, default=0, nullable=False)

    # Pipeline stage
    stage = db.Column(db.String(40), default="New Lead", nullable=False)
    # Suggested stages:
    # "New Lead", "Contacted", "Interested", "Counseling Done", "Follow-up", "Converted", "Lost"

    # Follow-up tracking
    last_contact_date = db.Column(db.Date, nullable=True)
    next_followup_date = db.Column(db.Date, nullable=True)
    followup_count = db.Column(db.Integer, default=0, nullable=False)

    notes = db.Column(db.Text, nullable=True)

    # Status
    status = db.Column(db.String(20), default="active", nullable=False)
    # "active", "converted", "lost"

    lost_reason = db.Column(db.String(120), nullable=True)

    # Ownership (who is handling)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    assigned_to = db.relationship("User", backref=db.backref("assigned_leads", lazy=True))

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relations
    followups = db.relationship(
        "FollowUp",
        backref="lead",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="desc(FollowUp.created_at)"
    )

    def __repr__(self) -> str:
        return f"<Lead {self.id} {self.name} ({self.stage})>"


# ---------------------------
# FollowUp Model (Timeline)
# ---------------------------
class FollowUp(db.Model):
    __tablename__ = "followups"

    id = db.Column(db.Integer, primary_key=True)

    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=False)

    # who made this follow-up
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    user = db.relationship("User", backref=db.backref("followups", lazy=True))

    # follow-up details
    method = db.Column(db.String(30), nullable=True)   # Call/WhatsApp/Walk-in/Email
    outcome = db.Column(db.String(80), nullable=True)  # Interested/Callback later/Not interested etc.
    note = db.Column(db.Text, nullable=True)

    # scheduling
    next_followup_date = db.Column(db.Date, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<FollowUp {self.id} lead={self.lead_id}>"


# ---------------------------
# Activity Model (Audit Log)
# ---------------------------
class Activity(db.Model):
    __tablename__ = "activities"

    id = db.Column(db.Integer, primary_key=True)

    # who performed the action
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref=db.backref("activities", lazy=True))

    # what lead is involved
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=False)
    lead = db.relationship("Lead", backref=db.backref("activities", lazy=True))

    # type of action: "lead_created", "lead_edited", "stage_changed", "followup_added", "lead_converted", "lead_lost"
    action_type = db.Column(db.String(50), nullable=False, index=True)

    # description of what happened
    description = db.Column(db.Text, nullable=True)

    # optional: track what changed (field name)
    field_changed = db.Column(db.String(80), nullable=True)

    # optional: old and new values (for tracking changes)
    old_value = db.Column(db.String(255), nullable=True)
    new_value = db.Column(db.String(255), nullable=True)

    # when it happened
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<Activity {self.id} {self.action_type} by {self.user_id} on lead {self.lead_id}>"