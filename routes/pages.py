from flask import Blueprint, render_template, session, redirect, url_for

pages_bp = Blueprint("pages", __name__)

@pages_bp.route("/")
def index():
    return redirect(url_for("pages.login"))

@pages_bp.route("/login")
def login():
    return render_template("login.html")

@pages_bp.route("/signup")
def signup():
    return render_template("signup.html")

@pages_bp.route("/homepage")
def homepage():
    if "user_id" not in session:
        return redirect(url_for("pages.login"))
    return render_template("homepage.html")