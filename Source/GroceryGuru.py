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
import database
from database import create_user, create_ingredient, create_home_ingredient, get_user_count


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
	user_count = get_user_count()
	user_id = create_user(f"testuser{user_count}@test.com", "testUser", "TestPassword")
	item_id = create_ingredient(f"Bananas{user_id}", "Dole", user_id)
	home_ingredient_id = create_home_ingredient(5, '2023-03-23 00:00:00', '2023-03-30 00:00:00', item_id)
	return render_template("CreateUserTest.j2", user_id=user_id, item_id=item_id, home_ingredient_id=home_ingredient_id)

@app.route("/DisplayIngredients")
def display_ingredients_test():
	# get current user
	user_id = 1		# fix later

	# get user's home items
	home_ingredients: list = database.Select.get_HomeIngredients_by_Persons_id(user_id)

	# display!!!!!!
	return render_template("ViewItems.j2", user_id=user_id, home_ingredients=home_ingredients)




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