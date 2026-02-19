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
	find_matching_inventory_item, add_inventory_count,
	update_inventory_ingredient, soft_delete_inventory_ingredient,
	update_list_ingredient, soft_delete_list_ingredient,
)


app = Flask(__name__, static_url_path="/static")
app.secret_key = os.getenv("SECRET_KEY")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@app.context_processor
def inject_current_year():
	return {"current_year": date.today().year}


@app.template_filter("date_str")
def date_str_filter(d):
	"""Format date for display (YYYY-MM-DD). Handles datetime, date, or string."""
	if d is None:
		return ""
	return d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]


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


@app.route("/CreateList", methods=["POST"])
@login_required
def create_list_route():
	"""Create a new empty list and redirect to its view."""
	list_name = request.form.get("list_name", "").strip()
	if not list_name:
		return redirect(url_for("display_ingredients", user_id=current_user.id))
	user_id = current_user.id
	get_or_create_list(list_name, user_id)
	return redirect(url_for("display_ingredients", user_id=user_id, list_name=list_name))


@app.route("/ShoppingList/<int:user_id>")
@app.route("/ShoppingList/<int:user_id>/<path:list_name>")
@login_required
def display_ingredients(user_id: int, list_name: str = None):
	if current_user.id != user_id:
		return "Forbidden: You can only view your own items.", 403
	all_lists = database.Select.get_Lists_by_Persons_id(user_id)
	# Ensure Grocery list exists (create if user has no lists)
	if not all_lists:
		get_or_create_list("Grocery list", user_id)
		all_lists = database.Select.get_Lists_by_Persons_id(user_id)
	# If no list_name, default to Grocery list
	if not list_name and all_lists:
		grocery = next((l for l in all_lists if l.name == "Grocery list"), None)
		selected_list = grocery or all_lists[0]
	else:
		selected_list = next((l for l in all_lists if l.name == list_name), None) if list_name else (all_lists[0] if all_lists else None)
	list_ingredients = []
	if selected_list:
		list_ingredients = database.Select.get_ListIngredients_by_Lists_id(selected_list.id, user_id)
	return render_template("ViewItems.j2", user_id=user_id, all_lists=all_lists, selected_list=selected_list, list_ingredients=list_ingredients, current_page="view_items")


@app.route("/Pantry/<int:user_id>")
@login_required
def pantry(user_id: int):
	if current_user.id != user_id:
		return "Forbidden: You can only view your own pantry.", 403
	inventory_items = database.Select.get_InventoryIngredients_by_Persons_id(user_id)
	return render_template("Pantry.j2", user_id=user_id, inventory_items=inventory_items, current_page="pantry")


@app.route("/PantryItem/<int:item_id>", methods=["GET", "POST"])
@login_required
def pantry_item(item_id: int):
	row = database.Select.get_InventoryIngredient_by_id(item_id, current_user.id)
	if row is None:
		return "Item not found or you don't have access to it.", 404
	inv_item, ingredient = row
	if request.method == "POST":
		action = request.form.get("action")
		if action == "delete":
			soft_delete_inventory_ingredient(item_id)
			return redirect(url_for("pantry", user_id=current_user.id))
		if action == "update":
			try:
				quantity_str = request.form.get("quantity", str(inv_item.count)).strip()
				quantity = max(1, int(quantity_str))
			except (ValueError, TypeError):
				quantity = inv_item.count
			expiration_date_str = request.form.get("expiration_date", "").strip()
			notes = request.form.get("notes", "").strip()
			date_expires = None
			if expiration_date_str:
				try:
					date_expires = datetime.strptime(expiration_date_str, "%Y-%m-%d")
				except ValueError:
					pass
			update_inventory_ingredient(
				item_id,
				count=quantity,
				date_expires=date_expires,
				notes=notes if notes else None,
			)
			return redirect(url_for("pantry_item", item_id=item_id))
	# Refresh after possible update from another request
	row = database.Select.get_InventoryIngredient_by_id(item_id, current_user.id)
	if row is None:
		return redirect(url_for("pantry", user_id=current_user.id))
	inv_item, ingredient = row

	def _fmt_date(d):
		if d is None:
			return ""
		if hasattr(d, "strftime"):
			return d.strftime("%m/%d/%Y")
		s = str(d)[:10]  # YYYY-MM-DD
		if len(s) == 10 and s[4] == "-" and s[7] == "-":
			return f"{s[5:7]}/{s[8:10]}/{s[:4]}"
		return s

	return render_template(
		"PantryItem.j2",
		inv_item=inv_item,
		ingredient=ingredient,
		item_id=item_id,
		expiration_date_val=_fmt_date(getattr(inv_item, "date_expires", None)),
		notes_val=getattr(inv_item, "notes", None) or "",
		date_purchased_str=_fmt_date(getattr(inv_item, "date_purchased", None)),
		current_page="pantry",
	)


@app.route("/DeletePantryItem/<int:item_id>", methods=["POST"])
@login_required
def delete_pantry_item(item_id: int):
	row = database.Select.get_InventoryIngredient_by_id(item_id, current_user.id)
	if row is None:
		return "Item not found or you don't have access to it.", 404
	soft_delete_inventory_ingredient(item_id)
	redirect_to = request.form.get("redirect_to") or url_for("pantry", user_id=current_user.id)
	return redirect(redirect_to)


@app.route("/ListItem/<int:item_id>", methods=["GET", "POST"])
@login_required
def list_item(item_id: int):
	row = database.Select.get_ListIngredient_by_id(item_id, current_user.id)
	if row is None:
		return "Item not found or you don't have access to it.", 404
	list_ingredient, ingredient, lst = row
	if request.method == "POST":
		action = request.form.get("action")
		if action == "delete":
			soft_delete_list_ingredient(item_id)
			return redirect(url_for("display_ingredients", user_id=current_user.id, list_name=lst.name))
		if action == "update":
			try:
				quantity_str = request.form.get("quantity", str(list_ingredient.quantity)).strip()
				quantity = max(1, int(quantity_str))
			except (ValueError, TypeError):
				quantity = list_ingredient.quantity
			update_list_ingredient(item_id, quantity)
			return redirect(url_for("list_item", item_id=item_id))
	# Refresh after possible update
	row = database.Select.get_ListIngredient_by_id(item_id, current_user.id)
	if row is None:
		return redirect(url_for("display_ingredients", user_id=current_user.id))
	list_ingredient, ingredient, lst = row

	def _fmt_date(d):
		if d is None:
			return ""
		if hasattr(d, "strftime"):
			return d.strftime("%m/%d/%Y")
		s = str(d)[:10]
		if len(s) == 10 and s[4] == "-" and s[7] == "-":
			return f"{s[5:7]}/{s[8:10]}/{s[:4]}"
		return s

	date_added_str = _fmt_date(getattr(list_ingredient, "date_added", None))
	return render_template(
		"ListItem.j2",
		list_ingredient=list_ingredient,
		ingredient=ingredient,
		list=lst,
		item_id=item_id,
		date_added_str=date_added_str,
		current_page="view_items",
	)


@app.route("/DeleteListItem/<int:item_id>", methods=["POST"])
@login_required
def delete_list_item(item_id: int):
	row = database.Select.get_ListIngredient_by_id(item_id, current_user.id)
	if row is None:
		return "Item not found or you don't have access to it.", 404
	_, _, lst = row
	soft_delete_list_ingredient(item_id)
	redirect_to = request.form.get("redirect_to") or url_for("display_ingredients", user_id=current_user.id, list_name=lst.name)
	return redirect(redirect_to)


@app.route("/Logout")
@login_required
def logout():
	logout_user()
	return redirect("/Login")


def _get_destination_options(user_id: int):
	"""Build destination options: My pantry, Grocery list, custom lists, Add new."""
	lists = database.Select.get_Lists_by_Persons_id(user_id)
	# Always include Grocery list; add custom lists that aren't Grocery list
	custom_names = {lst.name for lst in lists if lst.name != "Grocery list"}
	options = [("pantry", "My pantry"), ("Grocery list", "Grocery list")]
	options.extend((name, name) for name in sorted(custom_names))
	options.append(("__new__", "➕ Add new list…"))
	return options


@app.route("/AddListItem", methods=["GET", "POST"])
@app.route("/AddListItem/<int:user_id>", methods=["GET", "POST"])
@login_required
def add_list_item(user_id: int = None):
	# Normalize: use current_user when no user_id or when it matches
	if user_id is not None and current_user.id != user_id:
		return "Forbidden: You can only add items to your own lists.", 403
	user_id = current_user.id
	dest_options = _get_destination_options(user_id)

	if request.method == "POST":
		try:
			destination = request.form.get("destination", "Grocery list").strip()
			new_list_name = request.form.get("new_list_name", "").strip()
			if destination == "__new__":
				destination = new_list_name or "Grocery list"
			item_name = request.form.get("item_name", "").strip()
			quantity = int(request.form.get("quantity", 1))
			if not item_name:
				raise ValueError("Item name is required.")

			ingredient_id = get_or_create_ingredient(item_name, user_id)
			now = datetime.utcnow()

			if destination == "pantry":
				create_inventory_ingredient(quantity, now, None, ingredient_id, None)
				return redirect(url_for("pantry", user_id=user_id))
			else:
				list_id = get_or_create_list(destination, user_id)
				create_list_ingredient(quantity, now, ingredient_id, list_id)
				return redirect(url_for("display_ingredients", user_id=user_id, list_name=destination))
		except ValueError as error:
			return render_template("AddListItem.j2", user_id=user_id, dest_options=dest_options, default_destination=request.form.get("destination", "Grocery list"), error=str(error), current_page="add_items")
		except Exception as error:
			traceback.print_exc()
			return render_template("AddListItem.j2", user_id=user_id, dest_options=dest_options, default_destination=request.form.get("destination", "Grocery list"), error=str(error), current_page="add_items")
	default_destination = request.args.get("for_list", "Grocery list")
	return render_template("AddListItem.j2", user_id=user_id, dest_options=dest_options, default_destination=default_destination, current_page="add_items")


# ————————————————————————————————— Scan pantry item (barcode) ———————————————————————————————— #
@app.route("/ScanPantryItem", methods=["GET"])
@login_required
def scan_pantry_item():
	dest_options = _get_destination_options(current_user.id)
	default_destination = request.args.get("for_list", "Grocery list")
	return render_template("ScanPantryItem.j2", dest_options=dest_options, default_destination=default_destination, current_page="scan_pantry")


@app.route("/AddPantryItem", methods=["POST"])
@login_required
def add_pantry_item():
	try:
		item_name = request.form.get("item_name", "").strip()
		quantity_str = request.form.get("quantity", "1").strip()
		expiration_date_str = request.form.get("expiration_date", "").strip()
		destination = request.form.get("destination", "pantry").strip()
		new_list_name = request.form.get("new_list_name", "").strip()
		if destination == "__new__":
			destination = new_list_name or "Grocery list"
		if not item_name:
			return jsonify({"success": False, "error": "Item name is required."}), 400
		try:
			quantity = max(1, int(quantity_str))
		except (ValueError, TypeError):
			quantity = 1
		user_id = current_user.id
		ingredient_id = get_or_create_ingredient(item_name, user_id)
		now = datetime.utcnow()

		if destination == "pantry":
			date_expires = None
			if expiration_date_str:
				try:
					date_expires = datetime.strptime(expiration_date_str, "%Y-%m-%d")
				except ValueError:
					date_expires = None
			existing_id = find_matching_inventory_item(ingredient_id, date_expires)
			if existing_id is not None:
				add_inventory_count(existing_id, quantity)
				msg = f"Added {quantity} to existing '{item_name}' in your pantry."
			else:
				create_inventory_ingredient(quantity, now, date_expires, ingredient_id, None)
				msg = f"Added {quantity} '{item_name}' to your pantry." if quantity > 1 else f"Added '{item_name}' to your pantry."
			return jsonify({"success": True, "message": msg, "redirect": url_for("pantry", user_id=user_id)})
		else:
			list_id = get_or_create_list(destination, user_id)
			create_list_ingredient(quantity, now, ingredient_id, list_id)
			msg = f"Added {quantity} '{item_name}' to {destination}." if quantity > 1 else f"Added '{item_name}' to {destination}."
			return jsonify({"success": True, "message": msg, "redirect": url_for("display_ingredients", user_id=user_id, list_name=destination)})
	except Exception as error:
		traceback.print_exc()
		return jsonify({"success": False, "error": str(error)}), 500


if __name__ == "__main__":
	app.run(host="localhost", port=8000, debug=True)