#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from flask import *
from flask_login import (login_user)
from flask_login import LoginManager
from flask_login import login_user
from datetime import datetime
import json
import os
import psycopg2
import Functions
from datetime import timedelta
import traceback
import werkzeug


#import DB_Connections
import database
from database import create_user, create_list, create_ingredient, create_list_ingredient, get_user_count


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
		print(error)									###########
		return None

	return active_user


# @app.before_request
# def make_session_permanent():
#     session.permanent = False



# ————————————————————————————————— Pre Login ———————————————————————————————— #
@app.route("/", methods=["GET", "POST"])
def index():
	#TODO: If not logged in, redirect user to /login
	return render_template("Index.j2")


@app.route("/Success")
def success():
	return render_template("Success.j2")


@app.route("/Login", methods=["GET", "POST"])
def login():
	if request.method == "POST":
		try:
			user = Functions.login_user(request)
			login_user(user, remember=True, duration=timedelta(days=1))
			return redirect("/Success")
		except Exception as error:
			traceback.print_exc()							###########
			print(error)									###########
			return render_template("Index.j2", error=error)
	else:
		return render_template("Index.j2")


@app.route("/CreateAccount", methods=["GET", "POST"])
def createAccount():
	if request.method == "POST":
		try:
			user = Functions.add_new_user(request)
			print(user)
			login_user(user, remember=True, duration=timedelta(days=1))
			return redirect("/Success")
		except Exception as error:
			traceback.print_exc()							###########
			print(error)									###########
			return render_template("CreateAccount.j2", error=error)
	else:
		return render_template("CreateAccount.j2")


@app.route("/CreateUserTest")
def create_user_test():
	user_count = get_user_count()
	user_id = create_user(f"testuser{user_count}@test.com", "testUser", "TestPassword")
	list_id = create_list(f"shopping", user_id)
	item_id1 = create_ingredient(f"Bananas{user_id}", user_id)
	list_ingredient_id1 = create_list_ingredient(5, '2023-03-23 00:00:00', item_id1, list_id)
	item_id2 = create_ingredient(f"Oranges{user_id}", user_id)
	list_ingredient_id2 = create_list_ingredient(5, '2023-03-23 00:00:00', item_id2, list_id)
	return render_template("CreateUserTest.j2", user_id=user_id, item_id=item_id1, list_ingredient_id=list_ingredient_id1)


@app.route("/DisplayIngredients/<int:user_id>")
def display_ingredients_test(user_id: int):
	# Get current user
	# user_id = 20		# fix later

	# Get user's home items
	list_ingredients: list = database.Select.get_ListIngredients_by_Persons_id(user_id)
	print(list_ingredients)
	# Display ingredients
	return render_template("ViewItems.j2", user_id=user_id, list_ingredients=list_ingredients)


@app.route("/AddListItem/<int:user_id>")
def add_list_item(user_id: int):

	return render_template("AddListItem.j2", user_id=user_id)















app.run(host="localhost", port=8000, debug=True)