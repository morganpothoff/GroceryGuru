#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from flask import *
from flask_login import (current_user, LoginManager, login_user, logout_user, login_required)
from flask_login import LoginManager
from flask_login import login_user
from datetime import datetime
import database.DatabaseConnection
import json
import os
import psycopg2
import Functions
from datetime import timedelta
import traceback
import werkzeug

#import DB_Connections


app = Flask(__name__, static_url_path="/static")
app.secret_key = os.getenv("SECRET_KEY")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
	try:
		active_user = Functions.get_user_by_id(user_id)
	except:
		traceback.print_exc()							###########
		print(error)										###########
		return None

	return active_user


@app.before_request
def make_session_permanent():
    session.permanent = False



######################### Pre Login #########################
@app.route("/")
def openingHome():
	return render_template("OpeningHome.html")


@app.route("/Login", methods=["GET", "POST"])
def login():
	if request.method == "POST":
		try:
			user = Functions.login_user(request)
			login_user(user, remember=True, duration=timedelta(days=1))
			# return redirect("Home", args=(request))
			return redirect("Home")
		except Exception as error:
			traceback.print_exc()							###########
			print(error)										###########
			return render_template("Login.html", error=error)
	else:
		return render_template("Login.html")


@app.route("/ResetPassword")
def resetPassword():
	return render_template("ResetPassword.html")


@app.route("/CreateAccount", methods=["GET", "POST"])
def createAccount():
	if request.method == "POST":
		try:
			user = Functions.add_new_user(request)
			login_user(user, remember=True)
			return redirect("Home")
		except Exception as error:
			traceback.print_exc()							###########
			print(error)										###########
			return render_template("CreateAccount.html", error=error)
	else:
		return render_template("CreateAccount.html")



######################## Post Login #########################
   ######################## Lists ########################
@app.route("/Home")
# @app.route("/Home/<request>")
@login_required
def home():
# def home(request: werkzeug.local.LocalProxy):
	# Get username from request
	print(current_user)
	return render_template("Home.html", username=current_user.username)
	# return render_template("Home.html", username="Some crap")


@app.route("/MyPantry")
@login_required
def myPantry():
	return render_template("MyPantry.html")


@app.route("/MyFridge")
@login_required
def myFridge():
	return render_template("MyFridge.html")


@app.route("/MySpices")
@login_required
def mySpices():
	return render_template("MySpices.html")


@app.route("/MyTools")
@login_required
def myTools():
	return render_template("MyTools.html")


@app.route("/Recipes")
@login_required
def recipes():
	return render_template("Recipes.html")



   ######################## Other ########################
@app.route("/About")
@login_required
def about():
	return render_template("About.html")


@app.route("/MyAccount")
@login_required
def myAccount():
	return render_template("AccountInfo.html")


@app.route('/Logout', methods=['GET'])
@login_required
def logout():
	logout_user()
	return render_template("OpeningHome.html")



app.run(host="localhost", port=8000, debug=True)