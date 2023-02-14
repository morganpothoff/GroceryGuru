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
	except Exception as error:
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
	return render_template("OpeningHome.j2")


@app.route("/Login", methods=["GET", "POST"])
def login():
	if request.method == "POST":
		try:
			user = Functions.login_user(request)
			login_user(user, remember=True, duration=timedelta(days=1))
			return redirect("Home")
		except Exception as error:
			traceback.print_exc()							###########
			print(error)										###########
			return render_template("Login.j2", error=error)
	else:
		return render_template("Login.j2")


# TODO
@app.route("/ResetPassword")
def resetPassword():
	return render_template("ResetPassword.j2")


@app.route("/CreateAccount", methods=["GET", "POST"])
def createAccount():
	if request.method == "POST":
		try:
			user = Functions.add_new_user(request)
			print(user)
			login_user(user, remember=True, duration=timedelta(days=1))
			return redirect("Home")
		except Exception as error:
			return render_template("CreateAccount.j2", error=error)
	else:
		return render_template("CreateAccount.j2")



######################## Post Login #########################
   ######################## Lists ########################
@app.route("/Home")
@login_required
def home():
	# Get username from request
	print(current_user)
	return render_template("Home.j2", username=current_user.username)


@app.route("/ViewItems")
@login_required
def viewItems():
	return render_template("ViewItems.j2", username=current_user.username)


@app.route("/AddItems", methods=["GET", "POST"])
@login_required
def addItems():
	if(request.method == "GET"):
		ListsQuery: list = Functions.get_all_lists_by_user_id(current_user.id)
		dictionary_from_list = {dictionary["ListID"]: dictionary["Name"] for dictionary in ListsQuery}
		
		return render_template("AddItems.j2", username=current_user.username, DefaultList=dictionary_from_list, datetime=datetime.now())

	# if(request.method == "POST"):
	# 	try:
	# 		user = Functions.add_new_item(request)
	# 		print(user)
	# 		login_user(user, remember=True, duration=timedelta(days=1))
	# 		return redirect("Home")
	# 	except Exception as error:
	# 		return render_template("CreateAccount.j2", error=error)


@app.route("/MyPantry")
@login_required
def myPantry():
	return render_template("MyPantry.j2", username=current_user.username)


@app.route("/MyFridge")
@login_required
def myFridge():
	return render_template("MyFridge.j2", username=current_user.username)


@app.route("/MySpices")
@login_required
def mySpices():
	return render_template("MySpices.j2", username=current_user.username)


@app.route("/MyTools")
@login_required
def myTools():
	return render_template("MyTools.j2", username=current_user.username)


@app.route("/Recipes")
@login_required
def recipes():
	return render_template("Recipes.j2", username=current_user.username)



   ######################## Other ########################
@app.route("/About")
@login_required
def about():
	return render_template("About.j2", username=current_user.username)


@app.route("/MyAccount")
@login_required
def myAccount():
	return render_template("AccountInfo.j2", username=current_user.username)


@app.route('/Logout', methods=['GET'])
@login_required
def logout():
	logout_user()
	return render_template("OpeningHome.j2")



app.run(host="localhost", port=8000, debug=True)