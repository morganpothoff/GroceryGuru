#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from flask import *
from flask_login import (current_user, LoginManager, login_user, logout_user, login_required)
from flask_login import LoginManager
from flask_login import login_user
from datetime import datetime
import json
import os
import psycopg2
from datetime import timedelta
import traceback
import werkzeug


#import DB_Connections
from database import create_user, create_ingredient


app = Flask(__name__, static_url_path="/static")
app.secret_key = os.getenv("SECRET_KEY")

# login_manager = LoginManager()
# login_manager.init_app(app)
# login_manager.login_view = "login"


# @login_manager.user_loader
# def load_user(user_id):
# 	try:
# 		active_user = Functions.get_user_by_id(user_id)
# 	except:
# 		traceback.print_exc()							###########
# 		print(error)										###########
# 		return None

# 	return active_user


# @app.before_request
# def make_session_permanent():
#     session.permanent = False



# ————————————————————————————————— Pre Login ———————————————————————————————— #
@app.route("/")
def index():
	return render_template("Index.j2")


@app.route("/CreateUserTest")
def create_user_test():
	create_user()
	return ""


@app.route("/CreateIngredientTest")
def create_ingredient_test():
	create_ingredient()
	return ""


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
			return render_template("Login.html", error=error)
	else:
		return render_template("Login.html")



@app.route("/CreateAccount", methods=["GET", "POST"])
def createAccount():
	if request.method == "POST":
		try:
			user = Functions.add_new_user(request)
			print(user)
			login_user(user, remember=True, duration=timedelta(days=1))
			return redirect("Home")
		except Exception as error:
			traceback.print_exc()							###########
			print(error)										###########
			return render_template("CreateAccount.html", error=error)
	else:
		return render_template("CreateAccount.html")







app.run(host="localhost", port=8000, debug=True)