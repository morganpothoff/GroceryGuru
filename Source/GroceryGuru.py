#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from flask import *
from flask_login import login_user, logout_user, login_required, current_user
from flask_login import LoginManager
from datetime import datetime, date
import json
import os
import Functions
from datetime import timedelta
import traceback
import werkzeug


#import DB_Connections
import database
from database import (
	create_user, create_list, create_ingredient, create_list_ingredient, get_user_count,
	get_or_create_list, get_or_create_ingredient, create_inventory_ingredient,
)


app = Flask(__name__, static_url_path="/static")
app.secret_key = os.getenv("SECRET_KEY")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@app.context_processor
def inject_current_year():
	return {"current_year": date.today().year}


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
	if not current_user.is_authenticated:
		return redirect("/Login")
	return render_template("Home.j2", current_page="home")


@app.route("/Success")
@login_required
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


@app.route("/Profile", methods=["GET"])
def profile():
	return render_template("Profile.j2")


@app.route("/FAQ")
def faq():
	return render_template("FAQ.j2")


@app.route("/Privacy")
def privacy():
	return render_template("Placeholder.j2", title="Privacy Policy", page_name="Privacy Policy")


@app.route("/Terms")
def terms():
	return render_template("Placeholder.j2", title="Terms of Service", page_name="Terms of Service")


@app.route("/Contact")
def contact():
	return render_template("Placeholder.j2", title="Contact", page_name="Contact")


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
@login_required
def display_ingredients_test(user_id: int):
	if current_user.id != user_id:
		return "Forbidden: You can only view your own items.", 403
	list_ingredients: list = database.Select.get_ListIngredients_by_Persons_id(user_id)
	return render_template("ViewItems.j2", user_id=user_id, list_ingredients=list_ingredients, current_page="view_items")


@app.route("/Pantry/<int:user_id>")
@login_required
def pantry(user_id: int):
	if current_user.id != user_id:
		return "Forbidden: You can only view your own pantry.", 403
	inventory_items = database.Select.get_InventoryIngredients_by_Persons_id(user_id)
	return render_template("Pantry.j2", user_id=user_id, inventory_items=inventory_items, current_page="pantry")


@app.route("/Logout")
@login_required
def logout():
	logout_user()
	return redirect("/Login")


@app.route("/AddListItem", methods=["GET", "POST"])
@app.route("/AddListItem/<int:user_id>", methods=["GET", "POST"])
@login_required
def add_list_item(user_id: int = None):
	# Normalize: use current_user when no user_id or when it matches
	if user_id is not None and current_user.id != user_id:
		return "Forbidden: You can only add items to your own lists.", 403
	user_id = current_user.id

	if request.method == "POST":
		try:
			list_name = request.form.get("list_name", "Shopping List").strip()
			item_name = request.form.get("item_name", "").strip()
			quantity = int(request.form.get("quantity", 1))
			if not item_name:
				raise ValueError("Item name is required.")
			list_id = get_or_create_list(list_name, user_id)
			ingredient_id = get_or_create_ingredient(item_name, user_id)
			from datetime import datetime
			create_list_ingredient(quantity, datetime.utcnow(), ingredient_id, list_id)
			return redirect(f"/DisplayIngredients/{user_id}")
		except ValueError as error:
			return render_template("AddListItem.j2", user_id=user_id, error=str(error), current_page="add_items")
		except Exception as error:
			traceback.print_exc()
			return render_template("AddListItem.j2", user_id=user_id, error=str(error), current_page="add_items")
	return render_template("AddListItem.j2", user_id=user_id, current_page="add_items")


# ————————————————————————————————— Scan pantry item (barcode) ———————————————————————————————— #
@app.route("/ScanPantryItem", methods=["GET"])
@login_required
def scan_pantry_item():
	return render_template("ScanPantryItem.j2", current_page="scan_pantry")


@app.route("/AddPantryItem", methods=["POST"])
@login_required
def add_pantry_item():
	try:
		item_name = request.form.get("item_name", "").strip()
		expiration_date_str = request.form.get("expiration_date", "").strip()
		if not item_name:
			return jsonify({"success": False, "error": "Item name is required."}), 400
		user_id = current_user.id
		ingredient_id = get_or_create_ingredient(item_name, user_id)
		date_purchased = datetime.utcnow()
		date_expires = None
		if expiration_date_str:
			try:
				date_expires = datetime.strptime(expiration_date_str, "%Y-%m-%d")
			except ValueError:
				date_expires = None
		create_inventory_ingredient(1, date_purchased, date_expires, ingredient_id, None)
		return jsonify({"success": True, "message": f"Added '{item_name}' to your pantry."})
	except Exception as error:
		traceback.print_exc()
		return jsonify({"success": False, "error": str(error)}), 500















app.run(host="localhost", port=8000, debug=True)