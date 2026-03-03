# app.py
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, User, Lead, FollowUp
from utils.auth import admin_required
from utils.helpers import parse_date, utc_to_ist
from utils.lead_score import compute_lead_score

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # predefined dropdown options used across lead forms
    GENDER_OPTIONS = ["Male", "Female", "Other"]
    EDUCATION_OPTIONS = ["PUC", "Degree", "Working", "Job seeker"]
    STREAM_OPTIONS = ["Commerce", "Science", "Arts"]
    CAREER_GOAL_OPTIONS = ["Job", "Internship", "Skills", "Business"]
    LEAD_SOURCE_OPTIONS = ["Walk-in", "Instagram", "Referral", "Other"]
    TIMEFRAME_OPTIONS = ["Immediately", "1 week", "1 month", "Exploring"]

    FOLLOWUP_METHODS = ["Call", "WhatsApp", "Email", "In-person", "Other"]
    FOLLOWUP_OUTCOMES = ["Interested", "Call back", "Not interested", "No answer", "Other"]

    # Ensure instance folder exists
    import os
    os.makedirs(app.config["INSTANCE_DIR"], exist_ok=True)

    # Init DB
    db.init_app(app)

    # Login manager
    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Jinja filter for IST display
    @app.template_filter("ist")
    def ist_filter(dt):
        x = utc_to_ist(dt)
        if not x:
            return ""
        return x.strftime("%d-%b-%Y %I:%M %p")

    # Create tables + default users once
    with app.app_context():
        db.create_all()
        seed_default_users()

    # -----------------------
    # AUTH ROUTES
    # -----------------------
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

            user = User.query.filter_by(username=username).first()
            if not user or not user.check_password(password):
                flash("Invalid username or password", "danger")
                return render_template("login.html")

            if not user.is_active:
                flash("Your account is disabled. Contact admin.", "danger")
                return render_template("login.html")

            login_user(user)
            return redirect(url_for("dashboard"))

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    # -----------------------
    # DASHBOARD
    # -----------------------
    @app.route("/dashboard")
    @login_required
    def dashboard():
        today = date.today()

        new_leads_today = Lead.query.filter(db.func.date(Lead.created_at) == str(today)).count()

        followups_due = Lead.query.filter(
            Lead.status == "active",
            Lead.next_followup_date.isnot(None),
            Lead.next_followup_date <= today
        ).order_by(Lead.next_followup_date.asc()).all()

        hot_leads = Lead.query.filter(Lead.status == "active", Lead.lead_score >= 60).order_by(Lead.lead_score.desc()).limit(10).all()

        converted_this_month = Lead.query.filter(
            Lead.status == "converted",
            db.extract("month", Lead.updated_at) == today.month,
            db.extract("year", Lead.updated_at) == today.year
        ).count()

        total_active = Lead.query.filter(Lead.status == "active").count()

        return render_template(
            "dashboard.html",
            new_leads_today=new_leads_today,
            followups_due=followups_due[:10],
            followups_due_count=len(followups_due),
            hot_leads=hot_leads,
            converted_this_month=converted_this_month,
            total_active=total_active
        )

    # -----------------------
    # LEADS
    # -----------------------
    @app.route("/leads")
    @login_required
    def leads_list():
        q = request.args.get("q", "").strip()
        stage = request.args.get("stage", "").strip()
        source = request.args.get("source", "").strip()

        query = Lead.query

        if q:
            like = f"%{q}%"
            query = query.filter(
                db.or_(
                    Lead.name.ilike(like),
                    Lead.phone.ilike(like),
                    Lead.whatsapp.ilike(like)
                )
            )
        if stage:
            query = query.filter(Lead.stage == stage)
        if source:
            query = query.filter(Lead.lead_source == source)

        leads = query.order_by(Lead.updated_at.desc()).all()

        # Dropdown values
        stages = ["New Lead", "Contacted", "Interested", "Counseling Done", "Follow-up", "Converted", "Lost"]
        sources = [x[0] for x in db.session.query(Lead.lead_source).distinct().filter(Lead.lead_source.isnot(None)).all()]

        return render_template("leads.html", leads=leads, q=q, stage=stage, source=source, stages=stages, sources=sources)

    @app.route("/leads/new", methods=["GET", "POST"])
    @login_required
    def lead_create():
        if request.method == "POST":
            lead = Lead(
                name=request.form.get("name", "").strip(),
                phone=request.form.get("phone", "").strip(),
                whatsapp=request.form.get("whatsapp", "").strip() or None,
                gender=request.form.get("gender", "").strip() or None,
                age=int(request.form.get("age")) if request.form.get("age") else None,
                education_status=request.form.get("education_status", "").strip() or None,
                stream=request.form.get("stream", "").strip() or None,
                institute_name=request.form.get("institute_name", "").strip() or None,
                career_goal=request.form.get("career_goal", "").strip() or None,
                interested_courses=request.form.get("interested_courses", "").strip() or None,
                lead_source=request.form.get("lead_source", "").strip() or None,
                start_timeframe=request.form.get("start_timeframe", "").strip() or None,
                stage=request.form.get("stage", "New Lead").strip() or "New Lead",
                notes=request.form.get("notes", "").strip() or None,
            )

            lead.last_contact_date = parse_date(request.form.get("last_contact_date"))
            lead.next_followup_date = parse_date(request.form.get("next_followup_date"))

            lead.lead_score = compute_lead_score(lead.lead_source, lead.start_timeframe, lead.education_status, lead.career_goal)

            # assign to current user by default
            lead.assigned_to_id = current_user.id

            if not lead.name or not lead.phone:
                flash("Name and Phone are required.", "danger")
                return render_template(
                    "lead_form.html",
                    lead=None,
                    mode="create",
                    genders=GENDER_OPTIONS,
                    educations=EDUCATION_OPTIONS,
                    streams=STREAM_OPTIONS,
                    career_goals=CAREER_GOAL_OPTIONS,
                    lead_sources=LEAD_SOURCE_OPTIONS,
                    timeframes=TIMEFRAME_OPTIONS,
                )

            db.session.add(lead)
            db.session.commit()
            flash("Lead created successfully.", "success")
            return redirect(url_for("leads_list"))

        return render_template(
            "lead_form.html",
            lead=None,
            mode="create",
            genders=GENDER_OPTIONS,
            educations=EDUCATION_OPTIONS,
            streams=STREAM_OPTIONS,
            career_goals=CAREER_GOAL_OPTIONS,
            lead_sources=LEAD_SOURCE_OPTIONS,
            timeframes=TIMEFRAME_OPTIONS,
        )

    @app.route("/leads/<int:lead_id>")
    @login_required
    def lead_detail(lead_id):
        lead = Lead.query.get_or_404(lead_id)
        return render_template(
            "lead_detail.html",
            lead=lead,
            methods=FOLLOWUP_METHODS,
            outcomes=FOLLOWUP_OUTCOMES,
        )

    @app.route("/leads/<int:lead_id>/edit", methods=["GET", "POST"])
    @login_required
    def lead_edit(lead_id):
        lead = Lead.query.get_or_404(lead_id)

        if request.method == "POST":
            lead.name = request.form.get("name", "").strip()
            lead.phone = request.form.get("phone", "").strip()
            lead.whatsapp = request.form.get("whatsapp", "").strip() or None
            lead.gender = request.form.get("gender", "").strip() or None
            lead.age = int(request.form.get("age")) if request.form.get("age") else None

            lead.education_status = request.form.get("education_status", "").strip() or None
            lead.stream = request.form.get("stream", "").strip() or None
            lead.institute_name = request.form.get("institute_name", "").strip() or None

            lead.career_goal = request.form.get("career_goal", "").strip() or None
            lead.interested_courses = request.form.get("interested_courses", "").strip() or None
            lead.lead_source = request.form.get("lead_source", "").strip() or None
            lead.start_timeframe = request.form.get("start_timeframe", "").strip() or None

            lead.stage = request.form.get("stage", lead.stage).strip() or lead.stage
            lead.notes = request.form.get("notes", "").strip() or None

            lead.last_contact_date = parse_date(request.form.get("last_contact_date"))
            lead.next_followup_date = parse_date(request.form.get("next_followup_date"))

            # recompute score
            lead.lead_score = compute_lead_score(lead.lead_source, lead.start_timeframe, lead.education_status, lead.career_goal)

            # status auto-sync
            if lead.stage == "Converted":
                lead.status = "converted"
            elif lead.stage == "Lost":
                lead.status = "lost"
            else:
                lead.status = "active"

            db.session.commit()
            flash("Lead updated.", "success")
            return redirect(url_for("lead_detail", lead_id=lead.id))

        return render_template(
            "lead_form.html",
            lead=lead,
            mode="edit",
            genders=GENDER_OPTIONS,
            educations=EDUCATION_OPTIONS,
            streams=STREAM_OPTIONS,
            career_goals=CAREER_GOAL_OPTIONS,
            lead_sources=LEAD_SOURCE_OPTIONS,
            timeframes=TIMEFRAME_OPTIONS,
        )

    @app.route("/leads/<int:lead_id>/delete", methods=["POST"])
    @login_required
    def lead_delete(lead_id):
        lead = Lead.query.get_or_404(lead_id)
        db.session.delete(lead)
        db.session.commit()
        flash("Lead deleted.", "warning")
        return redirect(url_for("leads_list"))

    @app.route("/leads/<int:lead_id>/convert", methods=["POST"])
    @login_required
    def lead_convert(lead_id):
        lead = Lead.query.get_or_404(lead_id)
        lead.stage = "Converted"
        lead.status = "converted"
        lead.next_followup_date = None
        db.session.commit()
        flash("Lead marked as Converted.", "success")
        return redirect(url_for("lead_detail", lead_id=lead.id))

    @app.route("/leads/<int:lead_id>/mark_lost", methods=["POST"])
    @login_required
    def lead_mark_lost(lead_id):
        lead = Lead.query.get_or_404(lead_id)
        reason = request.form.get("lost_reason", "").strip() or None
        lead.stage = "Lost"
        lead.status = "lost"
        lead.lost_reason = reason
        lead.next_followup_date = None
        db.session.commit()
        flash("Lead marked as Lost.", "warning")
        return redirect(url_for("lead_detail", lead_id=lead.id))

    # -----------------------
    # FOLLOWUPS (today list)
    # -----------------------
    @app.route("/followups")
    @login_required
    def followups_today():
        today = date.today()
        leads = Lead.query.filter(
            Lead.status == "active",
            Lead.next_followup_date.isnot(None),
            Lead.next_followup_date <= today
        ).order_by(Lead.next_followup_date.asc()).all()

        return render_template("followups.html", leads=leads, today=today)

    # Add followup note to a lead
    @app.route("/leads/<int:lead_id>/followups/new", methods=["POST"])
    @login_required
    def followup_add(lead_id):
        lead = Lead.query.get_or_404(lead_id)
        method = request.form.get("method", "").strip() or None
        outcome = request.form.get("outcome", "").strip() or None
        note = request.form.get("note", "").strip() or None
        next_dt = parse_date(request.form.get("next_followup_date"))

        fu = FollowUp(
            lead_id=lead.id,
            user_id=current_user.id,
            method=method,
            outcome=outcome,
            note=note,
            next_followup_date=next_dt
        )
        db.session.add(fu)

        # update lead tracking
        lead.last_contact_date = date.today()
        lead.followup_count = (lead.followup_count or 0) + 1
        lead.next_followup_date = next_dt

        # stage nudge
        if lead.stage == "New Lead":
            lead.stage = "Contacted"

        db.session.commit()
        flash("Follow-up saved.", "success")
        return redirect(url_for("lead_detail", lead_id=lead.id))

    # -----------------------
    # PIPELINE
    # -----------------------
    @app.route("/pipeline")
    @login_required
    def pipeline():
        stages = ["New Lead", "Contacted", "Interested", "Counseling Done", "Follow-up", "Converted", "Lost"]
        data = {}
        for st in stages:
            data[st] = Lead.query.filter(Lead.stage == st).order_by(Lead.updated_at.desc()).limit(50).all()
        return render_template("pipeline.html", stages=stages, data=data)

    # quick stage update (buttons)
    @app.route("/leads/<int:lead_id>/stage", methods=["POST"])
    @login_required
    def lead_set_stage(lead_id):
        lead = Lead.query.get_or_404(lead_id)
        st = request.form.get("stage", "").strip()
        if st not in ["New Lead", "Contacted", "Interested", "Counseling Done", "Follow-up", "Converted", "Lost"]:
            abort(400)

        lead.stage = st
        if st == "Converted":
            lead.status = "converted"
            lead.next_followup_date = None
        elif st == "Lost":
            lead.status = "lost"
            lead.next_followup_date = None
        else:
            lead.status = "active"
        db.session.commit()
        return redirect(request.referrer or url_for("pipeline"))

    # -----------------------
    # REPORTS (admin only)
    # -----------------------
    @app.route("/reports")
    @login_required
    @admin_required
    def reports():
        today = date.today()
        total_leads = Lead.query.count()
        active = Lead.query.filter(Lead.status == "active").count()
        converted = Lead.query.filter(Lead.status == "converted").count()
        lost = Lead.query.filter(Lead.status == "lost").count()

        # source performance
        source_rows = db.session.query(
            Lead.lead_source,
            db.func.count(Lead.id)
        ).group_by(Lead.lead_source).all()

        # course interest (simple text contains)
        course_rows = db.session.query(
            Lead.interested_courses,
            db.func.count(Lead.id)
        ).group_by(Lead.interested_courses).all()

        return render_template(
            "reports.html",
            total_leads=total_leads,
            active=active,
            converted=converted,
            lost=lost,
            source_rows=source_rows,
            course_rows=course_rows
        )

    # -----------------------
    # USERS (admin only)
    # -----------------------
    @app.route("/users")
    @login_required
    @admin_required
    def users_list():
        users = User.query.order_by(User.created_at.desc()).all()
        return render_template("users.html", users=users)

    @app.route("/users/new", methods=["POST"])
    @login_required
    @admin_required
    def users_create():
        username = request.form.get("username", "").strip()
        full_name = request.form.get("full_name", "").strip() or None
        role = request.form.get("role", "counselor").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("users_list"))

        if role not in ["admin", "counselor"]:
            role = "counselor"

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("users_list"))

        u = User(username=username, full_name=full_name, role=role, is_active=True)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        flash("User created.", "success")
        return redirect(url_for("users_list"))

    @app.route("/users/<int:user_id>/toggle", methods=["POST"])
    @login_required
    @admin_required
    def users_toggle(user_id):
        u = User.query.get_or_404(user_id)
        if u.id == current_user.id:
            flash("You cannot disable your own account.", "warning")
            return redirect(url_for("users_list"))

        u.is_active = not u.is_active
        db.session.commit()
        flash("User status updated.", "success")
        return redirect(url_for("users_list"))

    @app.route("/users/<int:user_id>/reset_password", methods=["POST"])
    @login_required
    @admin_required
    def users_reset_password(user_id):
        u = User.query.get_or_404(user_id)
        password = request.form.get("new_password", "").strip()
        if not password:
            flash("Password cannot be empty.", "danger")
            return redirect(url_for("users_list"))
        u.set_password(password)
        db.session.commit()
        flash("Password reset successful.", "success")
        return redirect(url_for("users_list"))

    return app


def seed_default_users():
    """Create default users once, if none exist."""
    if User.query.count() > 0:
        return

    # Default Admin
    admin = User(username="naveen", full_name="Naveen", role="admin", is_active=True)
    admin.set_password("admin123")

    # Default Counselor
    counselor = User(username="chaithra", full_name="Chaithra", role="counselor", is_active=True)
    counselor.set_password("chaithra123")

    db.session.add(admin)
    db.session.add(counselor)
    db.session.commit()


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)