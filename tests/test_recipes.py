"""Unit tests for the Recipes feature: CRUD, routes, recipe extractor, and recipe images."""
import io

import pytest

from database import (
	create_user,
	create_recipe,
	update_recipe,
	soft_delete_recipe,
	create_recipe_image,
	delete_recipe_image,
)
from database import Select


# ————————————————————————————————— Fixtures ————————————————————————————————— #

@pytest.fixture
def test_user_id():
	"""Create a test user and return user_id."""
	email = f"recipe_{id(object())}@test.com"
	user_id = create_user(email, "Test User", "TestPass123")
	return user_id


@pytest.fixture
def test_recipe(test_user_id):
	"""Create a test recipe and return recipe_id."""
	rid = create_recipe(
		title="Chocolate Chip Cookies",
		Persons_id=test_user_id,
		ingredients="2 cups flour\n1 cup sugar\n1/2 cup butter",
		steps="Mix dry ingredients\nAdd wet ingredients\nBake at 350°F for 12 min",
		special_notes="Prep: 15 min. Cook: 12 min.",
		source_url="https://example.com/cookies",
		category="Desserts",
	)
	return rid


# ————————————————————————————————— Database: create ————————————————————————— #

class TestCreateRecipe:
	"""Tests for create_recipe database function."""

	def test_create_recipe_minimal(self, test_user_id):
		"""create_recipe with only title and user_id."""
		rid = create_recipe("Simple Recipe", test_user_id)
		assert rid is not None

		recipe = Select.get_Recipe_by_id(rid, test_user_id)
		assert recipe is not None
		assert recipe.title == "Simple Recipe"
		assert recipe.ingredients == ""
		assert recipe.steps == ""
		assert recipe.special_notes is None
		assert recipe.source_url is None
		assert recipe.category is None

	def test_create_recipe_full(self, test_user_id):
		"""create_recipe with all fields."""
		rid = create_recipe(
			title="Pancakes",
			Persons_id=test_user_id,
			ingredients="1 cup flour\n1 egg",
			steps="Mix and cook",
			special_notes="Serves 2",
			source_url="https://example.com/pancakes",
			category="Breakfasts",
		)
		recipe = Select.get_Recipe_by_id(rid, test_user_id)
		assert recipe.title == "Pancakes"
		assert "flour" in recipe.ingredients
		assert "Mix" in recipe.steps
		assert recipe.special_notes == "Serves 2"
		assert recipe.source_url == "https://example.com/pancakes"
		assert recipe.category == "Breakfasts"


# ————————————————————————————————— Database: update ———————————————————————— #

class TestUpdateRecipe:
	"""Tests for update_recipe database function."""

	def test_update_recipe_title(self, test_user_id, test_recipe):
		"""update_recipe changes title."""
		update_recipe(test_recipe, title="Updated Cookie Recipe")
		recipe = Select.get_Recipe_by_id(test_recipe, test_user_id)
		assert recipe.title == "Updated Cookie Recipe"

	def test_update_recipe_ingredients(self, test_user_id, test_recipe):
		"""update_recipe changes ingredients."""
		update_recipe(test_recipe, ingredients="3 cups flour\n2 cups sugar")
		recipe = Select.get_Recipe_by_id(test_recipe, test_user_id)
		assert "3 cups flour" in recipe.ingredients

	def test_update_recipe_clears_optional_fields(self, test_user_id, test_recipe):
		"""update_recipe can clear special_notes, source_url, category."""
		update_recipe(
			test_recipe,
			special_notes="",
			source_url="",
			category="",
		)
		recipe = Select.get_Recipe_by_id(test_recipe, test_user_id)
		assert recipe.special_notes is None
		assert recipe.source_url is None
		assert recipe.category is None


# ————————————————————————————————— Database: delete ———————————————————————— #

class TestDeleteRecipe:
	"""Tests for soft_delete_recipe database function."""

	def test_soft_delete_recipe(self, test_user_id, test_recipe):
		"""soft_delete_recipe hides recipe from get_Recipe_by_id."""
		soft_delete_recipe(test_recipe)
		recipe = Select.get_Recipe_by_id(test_recipe, test_user_id)
		assert recipe is None

	def test_soft_deleted_recipe_excluded_from_lists(self, test_user_id, test_recipe):
		"""get_Recipes_by_Persons_id excludes soft-deleted recipes."""
		recipes_before = Select.get_Recipes_by_Persons_id(test_user_id)
		assert len(recipes_before) >= 1

		soft_delete_recipe(test_recipe)

		recipes_after = Select.get_Recipes_by_Persons_id(test_user_id)
		ids_after = [r.id for r in recipes_after]
		assert test_recipe not in ids_after


# ————————————————————————————————— Database: Select ————————————————————————— #

class TestRecipeSelect:
	"""Tests for recipe Select helpers."""

	def test_get_Recipes_by_Persons_id(self, test_user_id, test_recipe):
		"""get_Recipes_by_Persons_id returns user's recipes ordered by title."""
		recipes = Select.get_Recipes_by_Persons_id(test_user_id)
		assert len(recipes) >= 1
		titles = [r.title for r in recipes]
		assert "Chocolate Chip Cookies" in titles

	def test_get_Recipes_by_category(self, test_user_id, test_recipe):
		"""get_Recipes_by_category filters by category."""
		desserts = Select.get_Recipes_by_category(test_user_id, "Desserts")
		assert len(desserts) >= 1
		assert all(r.category == "Desserts" for r in desserts)

	def test_get_Recipes_by_category_others(self, test_user_id):
		"""get_Recipes_by_category 'Others' returns uncategorized recipes."""
		rid = create_recipe("Uncategorized", test_user_id, category="")
		others = Select.get_Recipes_by_category(test_user_id, "Others")
		ids = [r.id for r in others]
		assert rid in ids

	def test_get_Recipe_by_id_returns_none_for_other_user(self, test_user_id, test_recipe):
		"""Users cannot access another user's recipe."""
		other_id = create_user("other_recipe@test.com", "Other", "pass")
		recipe = Select.get_Recipe_by_id(test_recipe, other_id)
		assert recipe is None

	def test_get_recipe_images_returns_empty_for_no_images(self, test_user_id, test_recipe):
		"""get_recipe_images returns empty list when recipe has no images."""
		images = Select.get_recipe_images(test_recipe)
		assert images == []

	def test_get_recipe_images_returns_ordered_by_sort_order(self, test_user_id, test_recipe):
		"""get_recipe_images returns images in sort_order (first uploaded first)."""
		create_recipe_image(test_recipe, "uploads/recipes/first.jpg")
		create_recipe_image(test_recipe, "uploads/recipes/second.jpg")
		create_recipe_image(test_recipe, "uploads/recipes/third.jpg")
		images = Select.get_recipe_images(test_recipe)
		assert len(images) == 3
		assert images[0].file_path == "uploads/recipes/first.jpg"
		assert images[1].file_path == "uploads/recipes/second.jpg"
		assert images[2].file_path == "uploads/recipes/third.jpg"


# ————————————————————————————————— Database: recipe images —————————————————— #

class TestRecipeImages:
	"""Tests for create_recipe_image and delete_recipe_image database functions."""

	def test_create_recipe_image(self, test_user_id, test_recipe):
		"""create_recipe_image adds an image and returns its id."""
		img_id = create_recipe_image(test_recipe, "uploads/recipes/test.jpg")
		assert img_id is not None
		images = Select.get_recipe_images(test_recipe)
		assert len(images) == 1
		assert images[0].id == img_id
		assert images[0].file_path == "uploads/recipes/test.jpg"

	def test_create_recipe_image_multiple_increments_sort_order(self, test_user_id, test_recipe):
		"""Multiple images get ascending sort_order (first uploaded = first displayed)."""
		create_recipe_image(test_recipe, "uploads/recipes/a.jpg")
		create_recipe_image(test_recipe, "uploads/recipes/b.jpg")
		images = Select.get_recipe_images(test_recipe)
		assert images[0].sort_order == 0
		assert images[1].sort_order == 1

	def test_delete_recipe_image(self, test_user_id, test_recipe):
		"""delete_recipe_image removes the image from the database."""
		img_id = create_recipe_image(test_recipe, "uploads/recipes/to_delete.jpg")
		assert len(Select.get_recipe_images(test_recipe)) == 1
		result = delete_recipe_image(test_recipe, img_id)
		assert result is True
		assert len(Select.get_recipe_images(test_recipe)) == 0

	def test_delete_recipe_image_returns_false_for_nonexistent(self, test_user_id, test_recipe):
		"""delete_recipe_image returns False when image id does not exist."""
		result = delete_recipe_image(test_recipe, 99999)
		assert result is False

	def test_delete_recipe_image_returns_false_for_wrong_recipe(self, test_user_id, test_recipe):
		"""delete_recipe_image returns False when image belongs to different recipe."""
		rid2 = create_recipe("Other Recipe", test_user_id)
		img_id = create_recipe_image(rid2, "uploads/recipes/other.jpg")
		result = delete_recipe_image(test_recipe, img_id)
		assert result is False
		assert len(Select.get_recipe_images(rid2)) == 1


# ————————————————————————————————— Routes: index & category ————————————————— #

class TestRecipesRoutes:
	"""Tests for recipe HTTP routes."""

	def test_recipes_index_requires_login(self, client):
		"""GET /Recipes redirects to login when not authenticated."""
		resp = client.get("/Recipes", follow_redirects=False)
		assert resp.status_code in (302, 401)
		if resp.status_code == 302:
			assert "Login" in resp.headers.get("Location", "")

	def test_recipes_index_logged_in(self, logged_in_client):
		"""GET /Recipes shows category links when authenticated."""
		client, user_id = logged_in_client
		resp = client.get("/Recipes", follow_redirects=True)
		assert resp.status_code == 200
		assert b"Recipes" in resp.data
		assert b"Desserts" in resp.data or b"Dinners" in resp.data
		assert b"Others" in resp.data

	def test_recipes_by_category(self, logged_in_client):
		"""GET /Recipes/<category> shows recipes in that category."""
		client, user_id = logged_in_client
		create_recipe("Test Dessert", user_id, category="Desserts")
		resp = client.get("/Recipes/Desserts", follow_redirects=True)
		assert resp.status_code == 200
		assert b"Test Dessert" in resp.data

	def test_recipes_add_requires_login(self, client):
		"""GET /Recipes/Add redirects to login when not authenticated."""
		resp = client.get("/Recipes/Add", follow_redirects=False)
		assert resp.status_code in (302, 401)


# ————————————————————————————————— Routes: add recipe ——————————————————————— #

class TestAddRecipeRoute:
	"""Tests for adding recipes via the web form."""

	def test_add_recipe_manual(self, logged_in_client):
		"""POST /Recipes/Add with manual data creates recipe."""
		client, user_id = logged_in_client
		resp = client.post(
			"/Recipes/Add",
			data={
				"title": "Manual Test Recipe",
				"ingredients": "flour\nsugar",
				"steps": "Mix and bake",
				"category": "Desserts",
			},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=True,
		)
		assert resp.status_code == 200

		recipes = Select.get_Recipes_by_Persons_id(user_id)
		titles = [r.title for r in recipes]
		assert "Manual Test Recipe" in titles

	def test_add_recipe_requires_title_for_manual(self, logged_in_client):
		"""POST /Recipes/Add without title returns error when no URL import."""
		client, user_id = logged_in_client
		resp = client.post(
			"/Recipes/Add",
			data={
				"title": "",
				"ingredients": "flour",
				"steps": "bake",
			},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=False,
		)
		assert resp.status_code == 400
		assert b"required" in resp.data.lower() or b"title" in resp.data.lower()


# ————————————————————————————————— Routes: recipe detail ——————————————————— #

class TestRecipeDetailRoute:
	"""Tests for recipe profile and edit/delete."""

	def test_recipe_detail_get(self, logged_in_client):
		"""GET /Recipe/<id> shows recipe when owned by user."""
		client, user_id = logged_in_client
		rid = create_recipe("Detail Test", user_id, ingredients="eggs")
		resp = client.get(f"/Recipe/{rid}", follow_redirects=True)
		assert resp.status_code == 200
		assert b"Detail Test" in resp.data
		assert b"eggs" in resp.data

	def test_recipe_detail_update(self, logged_in_client):
		"""POST to /Recipe/<id> with action=update saves changes."""
		client, user_id = logged_in_client
		rid = create_recipe("Original", user_id, ingredients="a")
		resp = client.post(
			f"/Recipe/{rid}",
			data={
				"action": "update",
				"title": "Updated Title",
				"ingredients": "a\nb",
				"steps": "Step 1",
				"source_url": "",
				"category": "Dinners",
			},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=True,
		)
		assert resp.status_code == 200

		recipe = Select.get_Recipe_by_id(rid, user_id)
		assert recipe.title == "Updated Title"
		assert "b" in recipe.ingredients
		assert recipe.category == "Dinners"

	def test_recipe_detail_delete(self, logged_in_client):
		"""POST to /Recipe/<id> with action=delete soft-deletes."""
		client, user_id = logged_in_client
		rid = create_recipe("To Delete", user_id)
		resp = client.post(
			f"/Recipe/{rid}",
			data={"action": "delete"},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=True,
		)
		assert resp.status_code == 200

		recipe = Select.get_Recipe_by_id(rid, user_id)
		assert recipe is None

	def test_recipe_detail_404_for_nonexistent(self, logged_in_client):
		"""GET /Recipe/99999 returns 404."""
		client, _ = logged_in_client
		resp = client.get("/Recipe/99999", follow_redirects=False)
		assert resp.status_code == 404

	def test_recipe_detail_404_for_other_user(self, logged_in_client, test_user_id, test_recipe):
		"""GET /Recipe/<id> returns 404 when recipe belongs to another user."""
		client, _ = logged_in_client
		# test_recipe owned by test_user_id; logged_in_client is a different user
		resp = client.get(f"/Recipe/{test_recipe}", follow_redirects=False)
		assert resp.status_code == 404

	def test_recipe_detail_shows_images_when_present(self, logged_in_client):
		"""GET /Recipe/<id> includes recipe images in the page when recipe has images."""
		client, user_id = logged_in_client
		rid = create_recipe("Recipe With Images", user_id)
		create_recipe_image(rid, "uploads/recipes/photo1.jpg")
		resp = client.get(f"/Recipe/{rid}", follow_redirects=True)
		assert resp.status_code == 200
		assert b"Recipe With Images" in resp.data
		assert b"uploads/recipes/photo1.jpg" in resp.data
		assert b"recipe-image-carousel" in resp.data


# ————————————————————————————————— Routes: recipe image upload ————————————————— #

class TestRecipeImageUpload:
	"""Tests for POST /Recipe/<id>/upload-image."""

	def test_upload_recipe_image_requires_login(self, client):
		"""POST /Recipe/1/upload-image redirects when not authenticated."""
		img = (io.BytesIO(b"fake image content"), "test.jpg")
		resp = client.post(
			"/Recipe/1/upload-image",
			data={"images": img},
			buffered=True,
			follow_redirects=False,
		)
		assert resp.status_code in (302, 401)
		if resp.status_code == 302:
			assert "Login" in resp.headers.get("Location", "")

	def test_upload_recipe_image_success(self, logged_in_client):
		"""POST /Recipe/<id>/upload-image uploads image and returns success."""
		client, user_id = logged_in_client
		rid = create_recipe("Upload Test", user_id)
		img = (io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF"), "photo.jpg")
		resp = client.post(
			f"/Recipe/{rid}/upload-image",
			data={"images": img},
			buffered=True,
		)
		assert resp.status_code == 200
		data = resp.get_json()
		assert data["success"] is True
		assert "images" in data
		assert len(data["images"]) == 1
		images = Select.get_recipe_images(rid)
		assert len(images) == 1
		assert "jpg" in images[0].file_path

	def test_upload_recipe_image_404_for_nonexistent(self, logged_in_client):
		"""POST /Recipe/99999/upload-image returns 404."""
		client, _ = logged_in_client
		img = (io.BytesIO(b"fake"), "test.jpg")
		resp = client.post(
			"/Recipe/99999/upload-image",
			data={"images": img},
			buffered=True,
		)
		assert resp.status_code == 404
		data = resp.get_json()
		assert data["success"] is False

	def test_upload_recipe_image_404_for_other_user_recipe(self, logged_in_client, test_user_id, test_recipe):
		"""POST /Recipe/<id>/upload-image returns 404 when recipe belongs to another user."""
		client, _ = logged_in_client
		img = (io.BytesIO(b"fake"), "test.jpg")
		resp = client.post(
			f"/Recipe/{test_recipe}/upload-image",
			data={"images": img},
			buffered=True,
		)
		assert resp.status_code == 404


# ————————————————————————————————— Routes: recipe image delete ————————————————— #

class TestRecipeImageDelete:
	"""Tests for POST /Recipe/<id>/delete-image/<image_id>."""

	def test_delete_recipe_image_requires_login(self, client):
		"""POST /Recipe/1/delete-image/1 redirects when not authenticated."""
		resp = client.post("/Recipe/1/delete-image/1", follow_redirects=False)
		assert resp.status_code in (302, 401)

	def test_delete_recipe_image_success(self, logged_in_client):
		"""POST /Recipe/<id>/delete-image/<image_id> deletes the image."""
		client, user_id = logged_in_client
		rid = create_recipe("Delete Image Test", user_id)
		img_id = create_recipe_image(rid, "uploads/recipes/to_delete.jpg")
		assert len(Select.get_recipe_images(rid)) == 1
		resp = client.post(
			f"/Recipe/{rid}/delete-image/{img_id}",
			follow_redirects=False,
		)
		assert resp.status_code == 200
		data = resp.get_json()
		assert data["success"] is True
		assert len(Select.get_recipe_images(rid)) == 0

	def test_delete_recipe_image_404_for_nonexistent_recipe(self, logged_in_client):
		"""POST /Recipe/99999/delete-image/1 returns 404."""
		client, _ = logged_in_client
		resp = client.post("/Recipe/99999/delete-image/1", follow_redirects=False)
		assert resp.status_code == 404

	def test_delete_recipe_image_404_for_other_user_recipe(self, logged_in_client, test_user_id, test_recipe):
		"""POST /Recipe/<id>/delete-image/<image_id> returns 404 when recipe belongs to another user."""
		client, _ = logged_in_client
		img_id = create_recipe_image(test_recipe, "uploads/recipes/other.jpg")
		resp = client.post(
			f"/Recipe/{test_recipe}/delete-image/{img_id}",
			follow_redirects=False,
		)
		assert resp.status_code == 404
		# Image should still exist (owned by test_user_id)
		assert len(Select.get_recipe_images(test_recipe)) == 1


# ————————————————————————————————— Routes: delete recipe ————————————————————— #

class TestDeleteRecipeRoute:
	"""Tests for DELETE /DeleteRecipe/<id>."""

	def test_delete_recipe_route(self, logged_in_client):
		"""POST /DeleteRecipe/<id> soft-deletes and redirects."""
		client, user_id = logged_in_client
		rid = create_recipe("Delete Route Test", user_id)
		resp = client.post(
			f"/DeleteRecipe/{rid}",
			data={"redirect_to": "/Recipes"},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=True,
		)
		assert resp.status_code == 200

		recipe = Select.get_Recipe_by_id(rid, user_id)
		assert recipe is None

	def test_delete_recipe_404_for_nonexistent(self, logged_in_client):
		"""POST /DeleteRecipe/99999 returns 404."""
		client, _ = logged_in_client
		resp = client.post(
			"/DeleteRecipe/99999",
			data={},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=False,
		)
		assert resp.status_code == 404


# ————————————————————————————————— Recipe extractor ———————————————————————— #

class TestRecipeExtractor:
	"""Tests for recipe_extractor module (no network calls)."""

	def test_normalize_category_desserts(self):
		"""Category detection maps dessert-related terms to Desserts."""
		from recipe_extractor import _normalize_category
		assert _normalize_category("Dessert") == "Desserts"
		assert _normalize_category("cookies") == "Desserts"
		assert _normalize_category("Cake") == "Desserts"

	def test_normalize_category_dinners(self):
		"""Category detection maps dinner-related terms to Dinners."""
		from recipe_extractor import _normalize_category
		assert _normalize_category("dinner") == "Dinners"
		assert _normalize_category("Main course") == "Dinners"

	def test_normalize_category_breakfasts(self):
		"""Category detection maps breakfast-related terms to Breakfasts."""
		from recipe_extractor import _normalize_category
		assert _normalize_category("breakfast") == "Breakfasts"
		assert _normalize_category("Brunch") == "Breakfasts"

	def test_normalize_category_others(self):
		"""Category detection returns empty for unrecognized."""
		from recipe_extractor import _normalize_category
		assert _normalize_category("") == ""
		assert _normalize_category("Snacks") == ""
		assert _normalize_category("Appetizer") == ""

	def test_extract_ingredients_from_schema_list(self):
		"""_extract_ingredients_from_schema handles list of strings."""
		from recipe_extractor import _extract_ingredients_from_schema
		obj = {"recipeIngredient": ["1 cup flour", "2 eggs"]}
		result = _extract_ingredients_from_schema(obj)
		assert "1 cup flour" in result
		assert "2 eggs" in result

	def test_extract_instructions_from_schema_howto_steps(self):
		"""_extract_instructions_from_schema handles HowToStep objects."""
		from recipe_extractor import _extract_instructions_from_schema
		obj = {
			"recipeInstructions": [
				{"@type": "HowToStep", "text": "Mix ingredients"},
				{"@type": "HowToStep", "text": "Bake for 20 min"},
			]
		}
		result = _extract_instructions_from_schema(obj)
		assert "Mix ingredients" in result
		assert "Bake for 20 min" in result
