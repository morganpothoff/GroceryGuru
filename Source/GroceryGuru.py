#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from flask import *
from flask_login import login_user, logout_user, login_required, current_user
from flask_login import LoginManager
from datetime import datetime, date
from pathlib import Path
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
	update_list, delete_list,
	create_recipe, update_recipe, soft_delete_recipe,
	upsert_recipe_rating, create_recipe_comment, create_recipe_image, delete_recipe_image,
	create_friend_request, accept_friend_request, decline_friend_request, unfriend,
	update_person_profile,
	share_recipe_with_friends, add_shared_recipe_to_user,
	dismiss_notification,
)
import recipe_extractor


app = Flask(__name__, static_url_path="/static")
app.secret_key = os.getenv("SECRET_KEY")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@app.context_processor
def inject_current_year():
	return {"current_year": date.today().year}


@app.context_processor
def inject_notifications():
	"""Inject pending friend request count, recipe shares, and total for bell icon (logged-in users only)."""
	if current_user.is_authenticated:
		pending = database.Select.get_pending_friend_requests_for_user(current_user.id)
		recipe_shares = database.Select.get_recipe_shares_for_recipient(current_user.id)
		total = len(pending) + len(recipe_shares)
		return {
			"notification_count": total,
			"pending_friend_requests": pending,
			"recipe_share_notifications": recipe_shares,
		}
	return {"notification_count": 0, "pending_friend_requests": [], "recipe_share_notifications": []}


@app.context_processor
def inject_user_lists():
	"""Inject user lists for nav dropdown (Grocery list first, then custom lists alphabetically)."""
	if current_user.is_authenticated:
		lists = database.Select.get_Lists_by_Persons_id(current_user.id)
		grocery = next((l for l in lists if l.name == "Grocery list"), None)
		custom = sorted([l for l in lists if l.name != "Grocery list"], key=lambda l: l.name)
		ordered = ([grocery] if grocery else []) + custom
		return {"user_lists": ordered}
	return {"user_lists": []}


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


@app.route("/Profile", methods=["GET", "POST"])
@login_required
def profile():
	"""Profile page with friend count, edit form, and theme toggle."""
	friend_count = database.Select.get_friend_count(current_user.id)
	if request.method == "POST":
		action = request.form.get("action")
		if action == "update_profile":
			try:
				name = request.form.get("name", "").strip()
				email = request.form.get("email", "").strip()
				update_person_profile(current_user.id, name=name or None, email=email or None)
				return redirect(url_for("profile"))
			except ValueError as e:
				return render_template("Profile.j2", friend_count=friend_count, profile_error=str(e))
	return render_template("Profile.j2", friend_count=friend_count)


@app.route("/FAQ")
def faq():
	return render_template("FAQ.j2")


@app.route("/Privacy")
def privacy():
	return render_template("Privacy.j2")


@app.route("/Terms")
def terms():
	return render_template("Terms.j2")


@app.route("/Contact")
def contact():
	return render_template("Contact.j2")


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
		redirect_to = request.form.get("redirect_to") or url_for("lists_index")
		return redirect(redirect_to)
	user_id = current_user.id
	get_or_create_list(list_name, user_id)
	redirect_to = request.form.get("redirect_to") or url_for("display_ingredients", user_id=user_id, list_name=list_name)
	return redirect(redirect_to)


@app.route("/Lists/Update", methods=["POST"])
@login_required
def update_lists_route():
	"""Update multiple list names. Form keys: list_<id>=<new_name>."""
	updated = 0
	for key, value in request.form.items():
		if key.startswith("list_") and key[5:].isdigit():
			list_id = int(key[5:])
			new_name = (value or "").strip()
			if new_name and update_list(list_id, new_name, current_user.id):
				updated += 1
	if updated:
		flash(f"{updated} list{'s' if updated != 1 else ''} updated.", "success")
	return redirect(url_for("lists_index"))


@app.route("/Lists/<int:list_id>/Delete", methods=["POST"])
@login_required
def delete_list_route(list_id: int):
	"""Delete a list and all its items."""
	if delete_list(list_id, current_user.id):
		flash("List and all its items have been deleted.", "success")
	else:
		flash("List not found or you don't have permission to delete it.", "error")
	return redirect(url_for("lists_index"))


@app.route("/Lists")
@login_required
def lists_index():
	"""All lists overview: show links to each list."""
	all_lists = database.Select.get_Lists_by_Persons_id(current_user.id)
	if not all_lists:
		get_or_create_list("Grocery list", current_user.id)
		all_lists = database.Select.get_Lists_by_Persons_id(current_user.id)
	grocery = next((l for l in all_lists if l.name == "Grocery list"), None)
	custom = sorted([l for l in all_lists if l.name != "Grocery list"], key=lambda l: l.name)
	ordered_lists = ([grocery] if grocery else []) + custom
	list_counts = {lst.id: len(database.Select.get_ListIngredients_by_Lists_id(lst.id, current_user.id)) for lst in ordered_lists}
	return render_template("ListsOverview.j2", user_id=current_user.id, all_lists=ordered_lists, list_counts=list_counts, current_page="lists")


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


# ————————————————————————————————— Recipes ———————————————————————————————— #
RECIPE_CATEGORIES = ["Desserts", "Dinners", "Breakfasts"]


def _get_pantry_ingredient_names(user_id: int):
	"""Return set of lowercase pantry ingredient names for matching."""
	rows = database.Select.get_InventoryIngredients_by_Persons_id(user_id)
	return {ing.name.strip().lower() for _, ing in rows if ing and ing.name}


def _count_pantry_matches(recipe_ingredients_text: str, pantry_names: set) -> int:
	"""Count how many pantry ingredients appear in recipe ingredient lines. Each pantry item counted at most once."""
	lines = [ln.strip() for ln in (recipe_ingredients_text or "").splitlines() if ln.strip()]
	line_lower = " ".join(lines).lower()
	matched = 0
	for name in pantry_names:
		if len(name) < 2:  # Skip very short names
			continue
		if name in line_lower:
			matched += 1
	return matched


def _recipe_ingredient_in_pantry(ingredient_line: str, pantry_names: set) -> bool:
	"""Check if a recipe ingredient line matches any pantry ingredient."""
	line_lower = (ingredient_line or "").strip().lower()
	if not line_lower:
		return False
	for name in pantry_names:
		if len(name) >= 2 and name in line_lower:
			return True
	return False


def _get_recipes_sorted_by_pantry_match(user_id: int, category: str = None):
	"""Return list of (recipe, match_count) sorted by match_count descending. category can be '' for Others, None for Any."""
	recipes = database.Select.get_Recipes_by_Persons_id(user_id)
	if category and str(category).strip():
		cat = category.strip()
		if cat.lower() == "others":
			recipes = [r for r in recipes if not (r.category or "").strip()]
		else:
			recipes = [r for r in recipes if (r.category or "").strip() == cat]
	pantry_names = _get_pantry_ingredient_names(user_id)
	scored = [(r, _count_pantry_matches(r.ingredients or "", pantry_names)) for r in recipes]
	scored.sort(key=lambda x: -x[1])  # Descending by match count
	return scored


@app.route("/Recipes")
@login_required
def recipes_index():
	"""Recipes home: show category links (Desserts, Dinners, Breakfasts, Others)."""
	all_recipes = database.Select.get_Recipes_by_Persons_id(current_user.id)
	# Build category counts
	category_counts = {}
	for cat in RECIPE_CATEGORIES:
		category_counts[cat] = sum(1 for r in all_recipes if (r.category or "").strip() == cat)
	category_counts["Others"] = sum(1 for r in all_recipes if not (r.category or "").strip())
	return render_template(
		"Recipes.j2",
		categories=RECIPE_CATEGORIES,
		category_counts=category_counts,
		current_page="recipes",
	)


@app.route("/Recipes/Add", methods=["GET", "POST"])
@login_required
def add_recipe():
	"""Add a recipe: manual form or import from URL."""
	if request.method == "POST":
		source_url = request.form.get("source_url", "").strip()
		title = request.form.get("title", "").strip()
		ingredients = request.form.get("ingredients", "")
		steps = request.form.get("steps", "")
		special_notes = request.form.get("special_notes", "")
		category = request.form.get("category", "").strip()
		# Import from URL when URL is provided and no manual title (user expects auto-import)
		if source_url and not title:
			try:
				from urllib.parse import urlparse
				parsed = urlparse(source_url)
				if not parsed.scheme:
					source_url = "https://" + source_url
				data = recipe_extractor.extract_recipe_from_url(source_url)
				if data:
					rid = create_recipe(
						title=data["title"],
						Persons_id=current_user.id,
						ingredients=data.get("ingredients", ""),
						steps=data.get("steps", ""),
						special_notes=data.get("special_notes", ""),
						source_url=data.get("source_url", source_url),
						category=data.get("category", ""),
						image_url=data.get("image_url", ""),
					)
					return redirect(url_for("recipe_detail", recipe_id=rid))
				# Extraction failed: show form with error and pre-filled URL
				return render_template(
					"AddRecipe.j2",
					error="Could not extract recipe from this URL. Add it manually below.",
					source_url=source_url,
					title="",
					ingredients="",
					steps="",
					special_notes="",
					category="",
					image_url="",
					current_page="recipes",
				)
			except Exception as e:
				traceback.print_exc()
				return render_template(
					"AddRecipe.j2",
					error=f"Could not fetch URL: {e}.",
					source_url=source_url,
					title="",
					ingredients="",
					steps="",
					special_notes="",
					category="",
					image_url="",
					current_page="recipes",
				)
		# Manual add
		image_url = request.form.get("image_url", "").strip()
		if not title:
			return render_template(
				"AddRecipe.j2",
				error="Recipe title is required.",
				source_url=source_url,
				ingredients=ingredients,
				steps=steps,
				special_notes=special_notes,
				category=category,
				image_url=image_url or "",
				current_page="recipes",
			), 400
		rid = create_recipe(
			title=title,
			Persons_id=current_user.id,
			ingredients=ingredients,
			steps=steps,
			special_notes=special_notes or None,
			source_url=source_url or None,
			category=category or None,
			image_url=image_url or None,
		)
		return redirect(url_for("recipe_detail", recipe_id=rid))
	return render_template("AddRecipe.j2", current_page="recipes")


@app.route("/FindRecipe", methods=["GET", "POST"])
@login_required
def find_recipe():
	"""Find a Recipe questionnaire: user selects recipe type, then we find best matches by pantry."""
	if request.method == "POST":
		recipe_type = request.form.get("recipe_type", "").strip()
		scored = _get_recipes_sorted_by_pantry_match(current_user.id, recipe_type or None)
		recipe_ids = [r.id for r, _ in scored]
		if not recipe_ids:
			return render_template(
				"FindRecipe.j2",
				error="No recipes match your criteria. Add some recipes first, or try a different category.",
				current_page="recipes",
			)
		# Redirect to results with ids and start at index 0
		ids_param = ",".join(str(i) for i in recipe_ids)
		return redirect(url_for("find_recipe_results", ids=ids_param, i=0))
	return render_template("FindRecipe.j2", current_page="recipes")


@app.route("/FindRecipe/Results")
@login_required
def find_recipe_results():
	"""Display recipe results with circular prev/next browsing. ids=comma-separated recipe IDs, i=current index."""
	ids_param = request.args.get("ids", "")
	idx_param = request.args.get("i", "0")
	try:
		recipe_ids = [int(x.strip()) for x in ids_param.split(",") if x.strip()]
		idx = int(idx_param)
	except (ValueError, TypeError):
		return redirect(url_for("find_recipe"))
	if not recipe_ids:
		return redirect(url_for("find_recipe"))
	# Circular index
	n = len(recipe_ids)
	idx = ((idx % n) + n) % n
	recipe_id = recipe_ids[idx]
	recipe = database.Select.get_Recipe_by_id(recipe_id, current_user.id)
	if recipe is None:
		return "Recipe not found.", 404
	ingredients_list = [ln.strip() for ln in (recipe.ingredients or "").splitlines() if ln.strip()]
	steps_list = [ln.strip() for ln in (recipe.steps or "").splitlines() if ln.strip()]
	pantry_names = _get_pantry_ingredient_names(current_user.id)
	match_count = _count_pantry_matches(recipe.ingredients or "", pantry_names)
	# For each ingredient, mark if in pantry
	ingredients_with_pantry = [(line, _recipe_ingredient_in_pantry(line, pantry_names)) for line in ingredients_list]
	recipe_images = database.Select.get_recipe_images(recipe_id)
	recipe_images_data = [{"url": url_for("static", filename=img.file_path), "id": img.id} for img in recipe_images]
	if not recipe_images_data and getattr(recipe, "image_url", None):
		recipe_images_data = [{"url": recipe.image_url, "id": None}]
	dest_options = _get_destination_options(current_user.id)
	prev_idx = (idx - 1) % n
	next_idx = (idx + 1) % n
	ids_param = ",".join(str(rid) for rid in recipe_ids)
	avg_rating = database.Select.get_recipe_average_rating(recipe_id)
	rating_count = database.Select.get_recipe_rating_count(recipe_id)
	user_rating = database.Select.get_user_recipe_rating(recipe_id, current_user.id)
	comments = database.Select.get_recipe_comments(recipe_id)
	friends = database.Select.get_friends(current_user.id)
	return render_template(
		"FindRecipeResults.j2",
		recipe=recipe,
		ingredients_list=ingredients_list,
		ingredients_with_pantry=ingredients_with_pantry,
		steps_list=steps_list,
		recipe_images_data=recipe_images_data,
		match_count=match_count,
		recipe_ids=recipe_ids,
		ids_param=ids_param,
		idx=idx,
		prev_idx=prev_idx,
		next_idx=next_idx,
		dest_options=dest_options,
		average_rating=avg_rating,
		rating_count=rating_count,
		user_rating=user_rating,
		comments=comments,
		friends=friends,
		categories=RECIPE_CATEGORIES,
		current_page="recipes",
	)


@app.route("/FindRecipe/AddToShoppingList", methods=["POST"])
@login_required
def find_recipe_add_to_list():
	"""Add recipe ingredients to shopping list. Optional: include ingredients already in pantry."""
	recipe_id = request.form.get("recipe_id", type=int)
	include_owned = request.form.get("include_owned") == "on"
	destination = request.form.get("destination", "Grocery list").strip()
	new_list_name = request.form.get("new_list_name", "").strip()
	if destination == "__new__":
		destination = new_list_name or "Grocery list"
	recipe = database.Select.get_Recipe_by_id(recipe_id, current_user.id)
	if recipe is None:
		return "Recipe not found.", 404
	ingredients_list = [ln.strip() for ln in (recipe.ingredients or "").splitlines() if ln.strip()]
	pantry_names = _get_pantry_ingredient_names(current_user.id)
	user_id = current_user.id
	now = datetime.utcnow()
	added = 0
	for line in ingredients_list:
		if not line:
			continue
		in_pantry = _recipe_ingredient_in_pantry(line, pantry_names)
		if not include_owned and in_pantry:
			continue
		ingredient_id = get_or_create_ingredient(line, user_id)
		list_id = get_or_create_list(destination, user_id)
		create_list_ingredient(1, now, ingredient_id, list_id)
		added += 1
	return redirect(url_for("display_ingredients", user_id=user_id, list_name=destination))


@app.route("/Recipe/Shared/<int:share_id>/AddToShoppingList", methods=["POST"])
@login_required
def shared_recipe_add_to_list(share_id: int):
	"""Add ingredients from a shared recipe to the user's list."""
	row = database.Select.get_recipe_share_by_id(share_id, current_user.id)
	if row is None:
		return "Shared recipe not found or you don't have access to it.", 404
	share, recipe, sharer = row
	include_owned = request.form.get("include_owned") == "on"
	destination = request.form.get("destination", "Grocery list").strip()
	new_list_name = request.form.get("new_list_name", "").strip()
	if destination == "__new__":
		destination = new_list_name or "Grocery list"
	ingredients_list = [ln.strip() for ln in (recipe.ingredients or "").splitlines() if ln.strip()]
	pantry_names = _get_pantry_ingredient_names(current_user.id)
	user_id = current_user.id
	now = datetime.utcnow()
	added = 0
	for line in ingredients_list:
		if not line:
			continue
		in_pantry = _recipe_ingredient_in_pantry(line, pantry_names)
		if not include_owned and in_pantry:
			continue
		ingredient_id = get_or_create_ingredient(line, user_id)
		list_id = get_or_create_list(destination, user_id)
		create_list_ingredient(1, now, ingredient_id, list_id)
		added += 1
	flash(f"Added {added} ingredient{'s' if added != 1 else ''} to {destination}.", "success")
	return redirect(url_for("display_ingredients", user_id=user_id, list_name=destination))


@app.route("/Recipes/<category>")
@login_required
def recipes_by_category(category: str):
	"""List recipes in a category (Desserts, Dinners, Breakfasts, Others)."""
	recipes = database.Select.get_Recipes_by_category(current_user.id, category)
	display_name = category if category and category != "Others" else "Others"
	return render_template(
		"RecipesCategory.j2",
		category=display_name,
		recipes=recipes,
		current_page="recipes",
	)


@app.route("/Recipe/<int:recipe_id>", methods=["GET", "POST"])
@login_required
def recipe_detail(recipe_id: int):
	"""Recipe profile: view, edit, delete, rate, and comment."""
	recipe = database.Select.get_Recipe_by_id(recipe_id, current_user.id)
	if recipe is None:
		return "Recipe not found or you don't have access to it.", 404
	if request.method == "POST":
		action = request.form.get("action")
		if action == "delete":
			soft_delete_recipe(recipe_id)
			return redirect(url_for("recipes_index"))
		if action == "update":
			update_recipe(
				recipe_id,
				title=request.form.get("title", "").strip(),
				ingredients=request.form.get("ingredients", ""),
				steps=request.form.get("steps", ""),
				special_notes=request.form.get("special_notes", "").strip() or None,
				source_url=request.form.get("source_url", "").strip() or None,
				category=request.form.get("category", "").strip() or None,
				image_url=request.form.get("image_url", "").strip() or None,
			)
			return redirect(url_for("recipe_detail", recipe_id=recipe_id))
		if action == "rate":
			try:
				rating = int(request.form.get("rating", 0))
				if 1 <= rating <= 5:
					upsert_recipe_rating(recipe_id, current_user.id, rating)
			except (ValueError, TypeError):
				pass
			return redirect(url_for("recipe_detail", recipe_id=recipe_id))
		if action == "comment":
			comment_body = request.form.get("comment_body", "").strip()
			if comment_body:
				try:
					create_recipe_comment(recipe_id, current_user.id, comment_body)
				except ValueError:
					pass
			return redirect(url_for("recipe_detail", recipe_id=recipe_id))
	recipe = database.Select.get_Recipe_by_id(recipe_id, current_user.id)
	if recipe is None:
		return redirect(url_for("recipes_index"))
	ingredients_list = [ln.strip() for ln in (recipe.ingredients or "").splitlines() if ln.strip()]
	steps_list = [ln.strip() for ln in (recipe.steps or "").splitlines() if ln.strip()]
	avg_rating = database.Select.get_recipe_average_rating(recipe_id)
	rating_count = database.Select.get_recipe_rating_count(recipe_id)
	user_rating = database.Select.get_user_recipe_rating(recipe_id, current_user.id)
	comments = database.Select.get_recipe_comments(recipe_id)
	recipe_images = database.Select.get_recipe_images(recipe_id)
	# Build list of {url, id}: uploaded images have id for delete; legacy image_url has id=None
	recipe_images_data = [{"url": url_for("static", filename=img.file_path), "id": img.id} for img in recipe_images]
	if not recipe_images_data and getattr(recipe, "image_url", None):
		recipe_images_data = [{"url": recipe.image_url, "id": None}]
	friends = database.Select.get_friends(current_user.id)
	dest_options = _get_destination_options(current_user.id)
	return render_template(
		"Recipe.j2",
		recipe=recipe,
		ingredients_list=ingredients_list,
		steps_list=steps_list,
		categories=RECIPE_CATEGORIES,
		average_rating=avg_rating,
		rating_count=rating_count,
		user_rating=user_rating,
		comments=comments,
		recipe_images_data=recipe_images_data,
		friends=friends,
		dest_options=dest_options,
		current_page="recipes",
	)


@app.route("/Recipe/<int:recipe_id>/share", methods=["POST"])
@login_required
def share_recipe(recipe_id: int):
	"""Share a recipe with selected friends. Expects JSON: {"recipient_ids": [1, 2, ...]}."""
	recipe = database.Select.get_Recipe_by_id(recipe_id, current_user.id)
	if recipe is None:
		return jsonify({"success": False, "error": "Recipe not found"}), 404
	data = request.get_json(silent=True) or {}
	recipient_ids = data.get("recipient_ids", [])
	if not isinstance(recipient_ids, list):
		recipient_ids = []
	recipient_ids = [int(x) for x in recipient_ids if str(x).isdigit()]
	if not recipient_ids:
		return jsonify({"success": False, "error": "Select at least one friend"}), 400
	success_count, errors = share_recipe_with_friends(recipe_id, current_user.id, recipient_ids)
	if success_count == 0:
		return jsonify({"success": False, "error": "; ".join(errors) if errors else "Could not share"}), 400
	msg = f"Recipe shared with {success_count} friend{'s' if success_count != 1 else ''}."
	if errors:
		msg += " " + "; ".join(errors[:3])
	return jsonify({"success": True, "message": msg, "shared_count": success_count})


@app.route("/Recipe/<int:recipe_id>/delete-image/<int:image_id>", methods=["POST"])
@login_required
def delete_recipe_image_route(recipe_id: int, image_id: int):
	"""Delete a recipe image (only for RecipeImages, not legacy image_url)."""
	recipe = database.Select.get_Recipe_by_id(recipe_id, current_user.id)
	if recipe is None:
		return jsonify({"success": False, "error": "Recipe not found"}), 404
	if delete_recipe_image(recipe_id, image_id):
		return jsonify({"success": True})
	return jsonify({"success": False, "error": "Image not found"}), 404


@app.route("/Recipe/<int:recipe_id>/upload-image", methods=["POST"])
@login_required
def upload_recipe_image(recipe_id: int):
	"""Upload one or more images for a recipe. Accepts multipart form with 'image' or 'images[]'."""
	recipe = database.Select.get_Recipe_by_id(recipe_id, current_user.id)
	if recipe is None:
		return jsonify({"success": False, "error": "Recipe not found"}), 404
	ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
	upload_dir = Path(app.root_path) / "static" / "uploads" / "recipes"
	upload_dir.mkdir(parents=True, exist_ok=True)
	files = request.files.getlist("images") or request.files.getlist("image")
	if not files or (len(files) == 1 and files[0].filename == ""):
		return jsonify({"success": False, "error": "No file selected"}), 400
	uploaded = []
	for f in files:
		if not f or not f.filename:
			continue
		ext = Path(f.filename).suffix.lower()
		if ext not in ALLOWED_EXT:
			continue
		import uuid
		stem = werkzeug.utils.secure_filename(Path(f.filename).stem) or "img"
		safe_name = f"{recipe_id}_{stem}_{uuid.uuid4().hex[:8]}{ext}"
		dest = upload_dir / safe_name
		f.save(str(dest))
		rel_path = f"uploads/recipes/{safe_name}"
		create_recipe_image(recipe_id, rel_path)
		uploaded.append(url_for("static", filename=rel_path))
	return jsonify({"success": True, "images": uploaded})


@app.route("/DeleteRecipe/<int:recipe_id>", methods=["POST"])
@login_required
def delete_recipe(recipe_id: int):
	recipe = database.Select.get_Recipe_by_id(recipe_id, current_user.id)
	if recipe is None:
		return "Recipe not found or you don't have access to it.", 404
	soft_delete_recipe(recipe_id)
	redirect_to = request.form.get("redirect_to") or url_for("recipes_index")
	return redirect(redirect_to)


# ————————————————————————————————— Friends ———————————————————————————————— #

@app.route("/Friends")
@login_required
def friends_list():
	"""Friends list page: display all friends, search, add friend."""
	friends = database.Select.get_friends(current_user.id)
	return render_template("Friends.j2", friends=friends, current_page="friends")


@app.route("/Friends/Add", methods=["GET", "POST"])
@login_required
def add_friend():
	"""Search for a user by email and send a friend request."""
	if request.method == "POST":
		email = request.form.get("email", "").strip()
		message = request.form.get("message", "").strip()
		if not email:
			return render_template("AddFriend.j2", error="Please enter an email address.")
		target = Functions.get_user_by_email(email)
		if target is None:
			return render_template("AddFriend.j2", error=f"No account found for '{email}'.")
		try:
			create_friend_request(current_user.id, target.id, message)
			return redirect(url_for("friends_list"))
		except ValueError as e:
			return render_template("AddFriend.j2", error=str(e))
	return render_template("AddFriend.j2")


@app.route("/Friends/Request/<int:request_id>/accept", methods=["POST"])
@login_required
def accept_friend_request_route(request_id: int):
	accept_friend_request(request_id, current_user.id)
	return redirect(request.referrer or url_for("friends_list"))


@app.route("/Friends/Request/<int:request_id>/decline", methods=["POST"])
@login_required
def decline_friend_request_route(request_id: int):
	decline_friend_request(request_id, current_user.id)
	return redirect(request.referrer or url_for("friends_list"))


@app.route("/Friends/Unfriend/<int:friend_id>", methods=["POST"])
@login_required
def unfriend_route(friend_id: int):
	unfriend(current_user.id, friend_id)
	return redirect(url_for("friends_list"))


@app.route("/Friends/Notifications")
@login_required
def notifications():
	"""Notifications page: pending friend requests and recipe shares."""
	pending = database.Select.get_pending_friend_requests_for_user(current_user.id)
	recipe_shares = database.Select.get_recipe_shares_for_recipient(current_user.id)
	return render_template("Notifications.j2", pending_requests=pending, recipe_shares=recipe_shares)


@app.route("/Notifications/Dismiss", methods=["POST"])
@login_required
def dismiss_notification_route():
	"""Dismiss a notification. Expects notification_type and notification_id in form."""
	notification_type = request.form.get("notification_type", "").strip().lower()
	notification_id = request.form.get("notification_id", type=int)
	if not notification_type or notification_id is None:
		return redirect(url_for("notifications"))
	if notification_type not in ("friend_request", "recipe_share"):
		return redirect(url_for("notifications"))
	dismiss_notification(current_user.id, notification_type, notification_id)
	return redirect(url_for("notifications"))


@app.route("/Recipe/Shared/<int:share_id>", methods=["GET", "POST"])
@login_required
def shared_recipe_detail(share_id: int):
	"""View a recipe shared with the current user. POST with action=add copies to their recipes."""
	row = database.Select.get_recipe_share_by_id(share_id, current_user.id)
	if row is None:
		return "Shared recipe not found or you don't have access to it.", 404
	share, recipe, sharer = row
	recipe_id = recipe.id
	# Dismiss the notification when user views the shared recipe
	dismiss_notification(current_user.id, "recipe_share", share_id)
	if request.method == "POST" and request.form.get("action") == "add":
		new_id = add_shared_recipe_to_user(share_id, current_user.id)
		if new_id:
			flash(f"Recipe added to your collection!", "success")
			return redirect(url_for("recipe_detail", recipe_id=new_id))
		else:
			flash("Could not add recipe.", "error")
	ingredients_list = [ln.strip() for ln in (recipe.ingredients or "").splitlines() if ln.strip()]
	steps_list = [ln.strip() for ln in (recipe.steps or "").splitlines() if ln.strip()]
	recipe_images = database.Select.get_recipe_images(recipe_id)
	recipe_images_data = [{"url": url_for("static", filename=img.file_path), "id": img.id} for img in recipe_images]
	if not recipe_images_data and getattr(recipe, "image_url", None):
		recipe_images_data = [{"url": recipe.image_url, "id": None}]
	dest_options = _get_destination_options(current_user.id)
	return render_template(
		"SharedRecipe.j2",
		share=share,
		recipe=recipe,
		sharer=sharer,
		ingredients_list=ingredients_list,
		steps_list=steps_list,
		recipe_images_data=recipe_images_data,
		dest_options=dest_options,
		current_page="recipes",
	)


if __name__ == "__main__":
	app.run(host="localhost", port=8000, debug=True)