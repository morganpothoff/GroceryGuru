"""Unit tests for the Find a Recipe feature: pantry matching, routes, and add to shopping list."""
from datetime import datetime

import pytest

from database import (
	create_user,
	create_recipe,
	create_inventory_ingredient,
	get_or_create_ingredient,
	create_list_ingredient,
	get_or_create_list,
)
from database import Select

# Import Find Recipe helpers from the app module
from GroceryGuru import (
	_get_pantry_ingredient_names,
	_count_pantry_matches,
	_recipe_ingredient_in_pantry,
	_get_recipes_sorted_by_pantry_match,
)


# ————————————————————————————————— Fixtures ————————————————————————————————— #

@pytest.fixture
def test_user_id():
	"""Create a test user and return user_id."""
	email = f"find_recipe_{id(object())}@test.com"
	user_id = create_user(email, "Test User", "TestPass123")
	return user_id


@pytest.fixture
def user_with_pantry(test_user_id):
	"""Create a user with flour, sugar, and eggs in pantry. Returns (user_id, [ingredient_names])."""
	ing_names = ["flour", "sugar", "eggs"]
	for name in ing_names:
		ing_id = get_or_create_ingredient(name, test_user_id)
		create_inventory_ingredient(1, datetime.utcnow(), None, ing_id, None)
	return (test_user_id, ing_names)


@pytest.fixture
def user_with_recipes(test_user_id):
	"""Create recipes with varying pantry overlap. Returns (user_id, recipe_ids)."""
	# Recipe A: flour, sugar, butter (2 pantry matches)
	rid_a = create_recipe(
		title="Sugar Cookies",
		Persons_id=test_user_id,
		ingredients="2 cups flour\n1 cup sugar\n1/2 cup butter",
		steps="Mix and bake",
		category="Desserts",
	)
	# Recipe B: flour, eggs, milk (2 pantry matches)
	rid_b = create_recipe(
		title="Pancakes",
		Persons_id=test_user_id,
		ingredients="1 cup flour\n2 eggs\n1/2 cup milk",
		steps="Mix and cook",
		category="Breakfasts",
	)
	# Recipe C: flour, sugar, eggs (3 pantry matches - best)
	rid_c = create_recipe(
		title="Cake",
		Persons_id=test_user_id,
		ingredients="2 cups flour\n1 cup sugar\n3 eggs",
		steps="Mix and bake",
		category="Desserts",
	)
	# Recipe D: chocolate, vanilla (0 pantry matches)
	rid_d = create_recipe(
		title="Chocolate Mousse",
		Persons_id=test_user_id,
		ingredients="8 oz chocolate\n1 tsp vanilla",
		steps="Melt and chill",
		category="Desserts",
	)
	return (test_user_id, [rid_a, rid_b, rid_c, rid_d])


# ————————————————————————————————— Helper functions ————————————————————————— #

class TestFindRecipeHelpers:
	"""Tests for _get_pantry_ingredient_names, _count_pantry_matches, _recipe_ingredient_in_pantry."""

	def test_get_pantry_ingredient_names_empty(self, test_user_id):
		"""_get_pantry_ingredient_names returns empty set when pantry is empty."""
		names = _get_pantry_ingredient_names(test_user_id)
		assert names == set()

	def test_get_pantry_ingredient_names_returns_lowercase(self, user_with_pantry):
		"""_get_pantry_ingredient_names returns lowercase names."""
		user_id, _ = user_with_pantry
		names = _get_pantry_ingredient_names(user_id)
		assert "flour" in names
		assert "sugar" in names
		assert "eggs" in names
		assert "Flour" not in names

	def test_count_pantry_matches_counts_substring(self):
		"""_count_pantry_matches counts when pantry name appears in recipe line."""
		pantry = {"flour", "sugar"}
		recipe = "2 cups flour\n1 cup sugar\n1/2 cup butter"
		assert _count_pantry_matches(recipe, pantry) == 2

	def test_count_pantry_matches_partial_match(self):
		"""_count_pantry_matches matches 'flour' in 'all-purpose flour'."""
		pantry = {"flour"}
		recipe = "2 cups all-purpose flour"
		assert _count_pantry_matches(recipe, pantry) == 1

	def test_count_pantry_matches_case_insensitive(self):
		"""_count_pantry_matches matches when recipe has different case (pantry names are lowercased in production)."""
		pantry = {"flour"}  # _get_pantry_ingredient_names returns lowercase
		recipe = "2 cups Flour"  # Recipe text can have any case
		assert _count_pantry_matches(recipe, pantry) == 1

	def test_count_pantry_matches_empty_pantry(self):
		"""_count_pantry_matches returns 0 for empty pantry."""
		assert _count_pantry_matches("flour and sugar", set()) == 0

	def test_count_pantry_matches_empty_recipe(self):
		"""_count_pantry_matches returns 0 for empty recipe."""
		assert _count_pantry_matches("", {"flour"}) == 0

	def test_recipe_ingredient_in_pantry_true(self):
		"""_recipe_ingredient_in_pantry returns True when pantry item in line."""
		pantry = {"flour", "eggs"}
		assert _recipe_ingredient_in_pantry("2 cups all-purpose flour", pantry) is True
		assert _recipe_ingredient_in_pantry("3 large eggs", pantry) is True

	def test_recipe_ingredient_in_pantry_false(self):
		"""_recipe_ingredient_in_pantry returns False when no match."""
		pantry = {"flour"}
		assert _recipe_ingredient_in_pantry("1 cup milk", pantry) is False
		assert _recipe_ingredient_in_pantry("8 oz chocolate", pantry) is False

	def test_recipe_ingredient_in_pantry_empty_line(self):
		"""_recipe_ingredient_in_pantry returns False for empty line."""
		assert _recipe_ingredient_in_pantry("", {"flour"}) is False


# ————————————————————————————————— _get_recipes_sorted_by_pantry_match ——————— #

class TestGetRecipesSortedByPantryMatch:
	"""Tests for _get_recipes_sorted_by_pantry_match."""

	def test_sorts_by_match_count_descending(self, user_with_pantry, user_with_recipes):
		"""Recipes are sorted by pantry match count, highest first."""
		user_id, _ = user_with_pantry
		_, recipe_ids = user_with_recipes
		scored = _get_recipes_sorted_by_pantry_match(user_id, None)
		# Cake has 3 matches, Sugar Cookies and Pancakes have 2, Chocolate Mousse has 0
		assert len(scored) >= 4
		# First should be Cake (3 matches)
		assert scored[0][0].title == "Cake"
		assert scored[0][1] == 3
		# Last should be Chocolate Mousse (0 matches)
		titles = [r.title for r, _ in scored]
		mousse_idx = titles.index("Chocolate Mousse")
		assert scored[mousse_idx][1] == 0

	def test_filters_by_category(self, user_with_pantry, user_with_recipes):
		"""When category=Desserts, only Desserts recipes returned."""
		user_id, _ = user_with_pantry
		user_with_recipes  # ensure recipes exist
		scored = _get_recipes_sorted_by_pantry_match(user_id, "Desserts")
		assert all((r.category or "").strip() == "Desserts" for r, _ in scored)

	def test_filters_by_others(self, test_user_id):
		"""When category=Others, only uncategorized recipes returned."""
		create_recipe("Uncategorized Recipe", test_user_id, category="")
		create_recipe("Dessert Recipe", test_user_id, category="Desserts")
		scored = _get_recipes_sorted_by_pantry_match(test_user_id, "Others")
		titles = [r.title for r, _ in scored]
		assert "Uncategorized Recipe" in titles
		assert "Dessert Recipe" not in titles

	def test_empty_category_returns_all(self, user_with_pantry, user_with_recipes):
		"""When category is None or empty, all recipes returned."""
		user_id, _ = user_with_pantry
		scored = _get_recipes_sorted_by_pantry_match(user_id, None)
		assert len(scored) >= 4
		scored2 = _get_recipes_sorted_by_pantry_match(user_id, "")
		assert len(scored2) == len(scored)


# ————————————————————————————————— Routes: Find Recipe ————————————————————— #

class TestFindRecipeRoutes:
	"""Tests for GET/POST /FindRecipe and GET /FindRecipe/Results."""

	def test_find_recipe_get_requires_login(self, client):
		"""GET /FindRecipe redirects to login when not authenticated."""
		resp = client.get("/FindRecipe", follow_redirects=False)
		assert resp.status_code in (302, 401)
		if resp.status_code == 302:
			assert "Login" in resp.headers.get("Location", "")

	def test_find_recipe_get_shows_form(self, logged_in_client):
		"""GET /FindRecipe shows the questionnaire form."""
		client, _ = logged_in_client
		resp = client.get("/FindRecipe", follow_redirects=True)
		assert resp.status_code == 200
		assert b"Find a Recipe" in resp.data
		assert b"recipe_type" in resp.data
		assert b"Find recipe" in resp.data

	def test_find_recipe_post_redirects_to_results(self, logged_in_client, user_with_recipes):
		"""POST /FindRecipe with recipe_type redirects to results."""
		client, user_id = user_with_recipes
		# Log in as this user (user_with_recipes creates its own user)
		email = f"find_recipe_{id(object())}@test.com"
		create_user(email, "Test User", "TestPass123")
		# Use logged_in_client's user - they share the same DB, so we need to create recipes for logged-in user
		client, user_id = logged_in_client
		create_recipe("Test Recipe", user_id, ingredients="flour", category="Desserts")
		resp = client.post(
			"/FindRecipe",
			data={"recipe_type": "Desserts"},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=False,
		)
		assert resp.status_code == 302
		loc = resp.headers.get("Location", "")
		assert "/FindRecipe/Results" in loc
		assert "ids=" in loc
		assert "i=0" in loc

	def test_find_recipe_post_no_recipes_shows_error(self, logged_in_client):
		"""POST /FindRecipe when no recipes match shows error message."""
		client, _ = logged_in_client
		# No recipes created
		resp = client.post(
			"/FindRecipe",
			data={"recipe_type": "Desserts"},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=False,
		)
		assert resp.status_code == 200
		assert b"No recipes" in resp.data or b"match" in resp.data.lower()

	def test_find_recipe_results_requires_login(self, client):
		"""GET /FindRecipe/Results redirects when not authenticated."""
		resp = client.get("/FindRecipe/Results?ids=1&i=0", follow_redirects=False)
		assert resp.status_code in (302, 401)

	def test_find_recipe_results_shows_recipe(self, logged_in_client):
		"""GET /FindRecipe/Results shows recipe and match count."""
		client, user_id = logged_in_client
		rid = create_recipe(
			"Best Match Recipe",
			user_id,
			ingredients="2 cups flour\n1 egg",
			category="Desserts",
		)
		resp = client.get(f"/FindRecipe/Results?ids={rid}&i=0", follow_redirects=True)
		assert resp.status_code == 200
		assert b"Best Match Recipe" in resp.data
		assert b"ingredient" in resp.data.lower()
		assert b"Prev" in resp.data or b"prev" in resp.data
		assert b"Next" in resp.data or b"next" in resp.data

	def test_find_recipe_results_circular_prev(self, logged_in_client):
		"""Prev at index 0 wraps to last recipe."""
		client, user_id = logged_in_client
		r1 = create_recipe("First", user_id, category="Desserts")
		r2 = create_recipe("Second", user_id, category="Desserts")
		# At index 0, prev should go to index 1 (last)
		resp = client.get(f"/FindRecipe/Results?ids={r1},{r2}&i=0", follow_redirects=True)
		assert resp.status_code == 200
		assert b"First" in resp.data
		# Prev link should have i=1
		assert b"i=1" in resp.data or "i=1" in resp.data.decode()

	def test_find_recipe_results_404_for_nonexistent_recipe(self, logged_in_client):
		"""GET /FindRecipe/Results with invalid recipe id returns 404."""
		client, user_id = logged_in_client
		rid = create_recipe("Mine", user_id)
		other_id = create_user("other@test.com", "Other", "pass")
		# Request with our recipe id but we need to ensure 404 for wrong user - actually our user owns rid
		# Test 404 for non-existent id
		resp = client.get("/FindRecipe/Results?ids=99999&i=0", follow_redirects=False)
		assert resp.status_code == 404

	def test_find_recipe_results_shows_unified_content(self, logged_in_client):
		"""FindRecipeResults shows ratings, comments, share, and add-to-list (unified recipe view)."""
		client, user_id = logged_in_client
		rid = create_recipe(
			"Unified View Recipe",
			user_id,
			ingredients="flour\nsugar",
			category="Desserts",
		)
		resp = client.get(f"/FindRecipe/Results?ids={rid}&i=0", follow_redirects=True)
		assert resp.status_code == 200
		assert b"Unified View Recipe" in resp.data
		# Ratings section
		assert b"Rate:" in resp.data or b"rating" in resp.data.lower()
		# Share button
		assert b"Share" in resp.data
		# Comments section
		assert b"Comments" in resp.data
		assert b"Add a comment" in resp.data or b"Post comment" in resp.data
		# Add to list form
		assert b"Add ingredients to shopping list" in resp.data
		assert b"Add to" in resp.data or b"destination" in resp.data.lower()
		# Checkboxes for ingredients/steps (cooking checklist)
		assert b"recipe-checkbox" in resp.data or b"checkbox" in resp.data.lower()


# ————————————————————————————————— Routes: Add to Shopping List ————————————— #

class TestFindRecipeAddToShoppingList:
	"""Tests for POST /FindRecipe/AddToShoppingList."""

	def test_add_to_list_requires_login(self, client):
		"""POST /FindRecipe/AddToShoppingList redirects when not authenticated."""
		resp = client.post(
			"/FindRecipe/AddToShoppingList",
			data={"recipe_id": "1", "destination": "Grocery list"},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=False,
		)
		assert resp.status_code in (302, 401)

	def test_add_to_list_excludes_owned_by_default(self, logged_in_client):
		"""When include_owned is unchecked, only missing ingredients are added."""
		client, user_id = logged_in_client
		# Add flour to pantry
		flour_id = get_or_create_ingredient("flour", user_id)
		create_inventory_ingredient(1, datetime.utcnow(), None, flour_id, None)
		# Recipe has flour and sugar
		rid = create_recipe(
			"Test",
			user_id,
			ingredients="2 cups flour\n1 cup sugar",
			category="Desserts",
		)
		resp = client.post(
			"/FindRecipe/AddToShoppingList",
			data={
				"recipe_id": str(rid),
				"destination": "Grocery list",
			},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=False,
		)
		assert resp.status_code == 302
		# Should add only sugar (flour is in pantry)
		lists = Select.get_Lists_by_Persons_id(user_id)
		grocery = next((l for l in lists if l.name == "Grocery list"), None)
		assert grocery is not None
		items = Select.get_ListIngredients_by_Lists_id(grocery.id, user_id)
		names = [ing.name for _, ing in items]
		assert "1 cup sugar" in names
		# Flour (or "2 cups flour") should NOT be in list since we have flour
		# Our matching: "flour" in "2 cups flour" -> match. So we skip it.
		assert not any("flour" in n.lower() for n in names)

	def test_add_to_list_includes_owned_when_checked(self, logged_in_client):
		"""When include_owned is checked, all ingredients are added."""
		client, user_id = logged_in_client
		flour_id = get_or_create_ingredient("flour", user_id)
		create_inventory_ingredient(1, datetime.utcnow(), None, flour_id, None)
		rid = create_recipe(
			"All Ingredients",
			user_id,
			ingredients="2 cups flour\n1 cup sugar",
			category="Desserts",
		)
		resp = client.post(
			"/FindRecipe/AddToShoppingList",
			data={
				"recipe_id": str(rid),
				"destination": "Grocery list",
				"include_owned": "on",
			},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=False,
		)
		assert resp.status_code == 302
		lists = Select.get_Lists_by_Persons_id(user_id)
		grocery = next((l for l in lists if l.name == "Grocery list"), None)
		assert grocery is not None
		items = Select.get_ListIngredients_by_Lists_id(grocery.id, user_id)
		names = [ing.name for _, ing in items]
		assert len(names) == 2
		assert "2 cups flour" in names
		assert "1 cup sugar" in names

	def test_add_to_list_404_for_nonexistent_recipe(self, logged_in_client):
		"""POST with recipe_id=99999 returns 404."""
		client, _ = logged_in_client
		resp = client.post(
			"/FindRecipe/AddToShoppingList",
			data={"recipe_id": "99999", "destination": "Grocery list"},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=False,
		)
		assert resp.status_code == 404

	def test_add_to_list_creates_new_list_when_destination_new(self, logged_in_client):
		"""When destination=__new__ and new_list_name provided, creates new list."""
		client, user_id = logged_in_client
		rid = create_recipe("Recipe", user_id, ingredients="salt", category="Desserts")
		resp = client.post(
			"/FindRecipe/AddToShoppingList",
			data={
				"recipe_id": str(rid),
				"destination": "__new__",
				"new_list_name": "Recipe Shopping",
			},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=False,
		)
		assert resp.status_code == 302
		loc = resp.headers.get("Location", "")
		assert "Recipe%20Shopping" in loc or "Recipe+Shopping" in loc
		lists = Select.get_Lists_by_Persons_id(user_id)
		names = [l.name for l in lists]
		assert "Recipe Shopping" in names
