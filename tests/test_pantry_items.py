"""Unit tests for adding, editing, and deleting pantry items."""
from datetime import datetime

import pytest

from database import (
	create_user,
	create_inventory_ingredient,
	get_or_create_ingredient,
	update_inventory_ingredient,
	soft_delete_inventory_ingredient,
	find_matching_inventory_item,
	add_inventory_count,
)
from database import Select


# ————————————————————————————————— Fixtures ————————————————————————————————— #

@pytest.fixture
def test_user_id():
	"""Create a test user and return user_id."""
	email = f"pantry_{id(object())}@test.com"
	user_id = create_user(email, "Test User", "TestPass123")
	return user_id


# ————————————————————————————————— Add pantry item —————————————————————————— #

class TestAddPantryItem:
	"""Tests for adding items to the pantry."""

	def test_add_pantry_item_api_new_item(self, logged_in_client):
		"""POST /AddPantryItem creates a new pantry item."""
		client, user_id = logged_in_client
		resp = client.post(
			"/AddPantryItem",
			data={
				"item_name": "Milk",
				"quantity": "2",
				"expiration_date": "2025-03-15",
			},
			content_type="application/x-www-form-urlencoded",
		)
		assert resp.status_code == 200
		data = resp.get_json()
		assert data["success"] is True
		assert "Milk" in data["message"]
		assert "Added" in data["message"]

		items = Select.get_InventoryIngredients_by_Persons_id(user_id)
		assert len(items) == 1
		inv_item, ingredient = items[0]
		assert ingredient.name == "Milk"
		assert inv_item.count == 2
		assert str(inv_item.date_expires).startswith("2025-03-15")

	def test_add_pantry_item_api_merges_existing(self, logged_in_client):
		"""Adding same item with same expiration merges quantity."""
		client, user_id = logged_in_client
		# First add
		client.post(
			"/AddPantryItem",
			data={"item_name": "Bread", "quantity": "1", "expiration_date": "2025-04-01"},
			content_type="application/x-www-form-urlencoded",
		)
		# Second add - same item and expiration
		resp = client.post(
			"/AddPantryItem",
			data={"item_name": "Bread", "quantity": "3", "expiration_date": "2025-04-01"},
			content_type="application/x-www-form-urlencoded",
		)
		assert resp.status_code == 200
		data = resp.get_json()
		assert data["success"] is True
		assert "existing" in data["message"].lower() or "Added" in data["message"]

		items = Select.get_InventoryIngredients_by_Persons_id(user_id)
		assert len(items) == 1
		inv_item, ingredient = items[0]
		assert ingredient.name == "Bread"
		assert inv_item.count == 4

	def test_add_pantry_item_api_requires_name(self, logged_in_client):
		"""POST /AddPantryItem returns 400 when item_name is missing."""
		client, _ = logged_in_client
		resp = client.post(
			"/AddPantryItem",
			data={"item_name": "", "quantity": "1"},
			content_type="application/x-www-form-urlencoded",
		)
		assert resp.status_code == 400
		data = resp.get_json()
		assert data["success"] is False
		assert "required" in data["error"].lower() or "name" in data["error"].lower()

	def test_add_pantry_item_api_default_quantity(self, logged_in_client):
		"""When quantity is missing or invalid, defaults to 1."""
		client, user_id = logged_in_client
		resp = client.post(
			"/AddPantryItem",
			data={"item_name": "Eggs"},
			content_type="application/x-www-form-urlencoded",
		)
		assert resp.status_code == 200
		items = Select.get_InventoryIngredients_by_Persons_id(user_id)
		assert len(items) == 1
		assert items[0][0].count == 1

	def test_create_inventory_ingredient(self, test_user_id):
		"""Database: create_inventory_ingredient inserts a new row."""
		ingredient_id = get_or_create_ingredient("Flour", test_user_id)
		inv_id = create_inventory_ingredient(
			count=5,
			date_purchased=datetime.utcnow(),
			date_expires=datetime(2025, 6, 1),
			Ingredients_id=ingredient_id,
			ListIngredients_id=None,
		)
		assert inv_id is not None

		row = Select.get_InventoryIngredient_by_id(inv_id, test_user_id)
		assert row is not None
		inv_item, ingredient = row
		assert ingredient.name == "Flour"
		assert inv_item.count == 5

	def test_find_matching_inventory_item_finds_same_expiration(self, test_user_id):
		"""find_matching_inventory_item returns id when same ingredient and expiration."""
		ingredient_id = get_or_create_ingredient("Yogurt", test_user_id)
		exp = datetime(2025, 5, 10)
		inv_id = create_inventory_ingredient(1, datetime.utcnow(), exp, ingredient_id, None)

		match_id = find_matching_inventory_item(ingredient_id, exp)
		assert match_id == inv_id

	def test_find_matching_inventory_item_none_when_different_expiration(self, test_user_id):
		"""find_matching_inventory_item returns None when expiration differs."""
		ingredient_id = get_or_create_ingredient("Cheese", test_user_id)
		create_inventory_ingredient(1, datetime.utcnow(), datetime(2025, 4, 1), ingredient_id, None)

		match_id = find_matching_inventory_item(ingredient_id, datetime(2025, 5, 1))
		assert match_id is None

	def test_add_inventory_count(self, test_user_id):
		"""add_inventory_count increases count."""
		ingredient_id = get_or_create_ingredient("Rice", test_user_id)
		inv_id = create_inventory_ingredient(2, datetime.utcnow(), None, ingredient_id, None)

		add_inventory_count(inv_id, 3)

		row = Select.get_InventoryIngredient_by_id(inv_id, test_user_id)
		assert row is not None
		assert row[0].count == 5


# ————————————————————————————————— Edit pantry item ————————————————————————— #

class TestEditPantryItem:
	"""Tests for editing pantry items."""

	def test_update_pantry_item_api(self, logged_in_client):
		"""POST to pantry_item with action=update saves changes."""
		client, user_id = logged_in_client
		# Add item first
		ingredient_id = get_or_create_ingredient("Cereal", user_id)
		inv_id = create_inventory_ingredient(
			1, datetime.utcnow(), datetime(2025, 8, 1), ingredient_id, None
		)

		resp = client.post(
			f"/PantryItem/{inv_id}",
			data={
				"action": "update",
				"quantity": "5",
				"expiration_date": "2025-09-15",
				"notes": "Whole grain",
			},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=True,
		)
		assert resp.status_code == 200

		row = Select.get_InventoryIngredient_by_id(inv_id, user_id)
		assert row is not None
		inv_item, ingredient = row
		assert inv_item.count == 5
		assert "2025-09-15" in str(inv_item.date_expires)
		assert getattr(inv_item, "notes", None) == "Whole grain"

	def test_update_pantry_item_api_clears_optional_fields(self, logged_in_client):
		"""Leaving expiration_date and notes empty clears them."""
		client, user_id = logged_in_client
		ingredient_id = get_or_create_ingredient("Jam", user_id)
		inv_id = create_inventory_ingredient(
			1, datetime.utcnow(), datetime(2025, 7, 1), ingredient_id, None
		)

		client.post(
			f"/PantryItem/{inv_id}",
			data={
				"action": "update",
				"quantity": "2",
				"expiration_date": "",
				"notes": "",
			},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=True,
		)

		row = Select.get_InventoryIngredient_by_id(inv_id, user_id)
		assert row is not None
		assert row[0].date_expires is None

	def test_update_inventory_ingredient_db(self, test_user_id):
		"""Database: update_inventory_ingredient updates count, date_expires, notes."""
		ingredient_id = get_or_create_ingredient("Honey", test_user_id)
		inv_id = create_inventory_ingredient(1, datetime.utcnow(), None, ingredient_id, None)

		update_inventory_ingredient(
			inv_id,
			count=10,
			date_expires=datetime(2026, 1, 1),
			notes="Local honey",
		)

		row = Select.get_InventoryIngredient_by_id(inv_id, test_user_id)
		assert row is not None
		inv_item, ingredient = row
		assert inv_item.count == 10
		assert "2026-01-01" in str(inv_item.date_expires)
		assert getattr(inv_item, "notes", None) == "Local honey"

	def test_update_inventory_ingredient_enforces_min_count(self, test_user_id):
		"""update_inventory_ingredient clamps count to at least 1."""
		ingredient_id = get_or_create_ingredient("Salt", test_user_id)
		inv_id = create_inventory_ingredient(5, datetime.utcnow(), None, ingredient_id, None)

		update_inventory_ingredient(inv_id, count=0, date_expires=None, notes=None)

		row = Select.get_InventoryIngredient_by_id(inv_id, test_user_id)
		assert row is not None
		assert row[0].count == 1

	def test_pantry_item_profile_requires_login(self, client):
		"""GET /PantryItem/<id> redirects to login when not authenticated."""
		resp = client.get("/PantryItem/1", follow_redirects=False)
		assert resp.status_code in (302, 401)
		# Typically redirects to login
		if resp.status_code == 302:
			assert "Login" in resp.headers.get("Location", "")


# ————————————————————————————————— Delete pantry item ——————————————————————— #

class TestDeletePantryItem:
	"""Tests for deleting pantry items."""

	def test_delete_pantry_item_profile_action(self, logged_in_client):
		"""POST to pantry_item with action=delete soft-deletes item."""
		client, user_id = logged_in_client
		ingredient_id = get_or_create_ingredient("ExpiredMilk", user_id)
		inv_id = create_inventory_ingredient(1, datetime.utcnow(), None, ingredient_id, None)

		resp = client.post(
			f"/PantryItem/{inv_id}",
			data={"action": "delete"},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=True,
		)
		assert resp.status_code == 200

		row = Select.get_InventoryIngredient_by_id(inv_id, user_id)
		assert row is None  # Soft-deleted items are filtered out

		items = Select.get_InventoryIngredients_by_Persons_id(user_id)
		assert len(items) == 0

	def test_delete_pantry_item_route(self, logged_in_client):
		"""POST /DeletePantryItem/<id> soft-deletes and redirects."""
		client, user_id = logged_in_client
		ingredient_id = get_or_create_ingredient("OldBread", user_id)
		inv_id = create_inventory_ingredient(1, datetime.utcnow(), None, ingredient_id, None)

		resp = client.post(
			f"/DeletePantryItem/{inv_id}",
			data={"redirect_to": f"/Pantry/{user_id}"},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=True,
		)
		assert resp.status_code == 200

		row = Select.get_InventoryIngredient_by_id(inv_id, user_id)
		assert row is None

	def test_delete_nonexistent_returns_404(self, logged_in_client):
		"""POST /DeletePantryItem/9999 returns 404 for non-existent item."""
		client, _ = logged_in_client
		resp = client.post(
			"/DeletePantryItem/99999",
			data={},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=False,
		)
		assert resp.status_code == 404

	def test_soft_delete_inventory_ingredient_db(self, test_user_id):
		"""Database: soft_delete_inventory_ingredient sets is_deleted=True."""
		ingredient_id = get_or_create_ingredient("TestItem", test_user_id)
		inv_id = create_inventory_ingredient(1, datetime.utcnow(), None, ingredient_id, None)

		soft_delete_inventory_ingredient(inv_id)

		row = Select.get_InventoryIngredient_by_id(inv_id, test_user_id)
		assert row is None

	def test_cannot_access_deleted_item_profile(self, logged_in_client):
		"""GET /PantryItem/<id> returns 404 for soft-deleted item."""
		client, user_id = logged_in_client
		ingredient_id = get_or_create_ingredient("DeletedItem", user_id)
		inv_id = create_inventory_ingredient(1, datetime.utcnow(), None, ingredient_id, None)

		soft_delete_inventory_ingredient(inv_id)

		resp = client.get(f"/PantryItem/{inv_id}", follow_redirects=False)
		assert resp.status_code == 404


# ————————————————————————————————— Select / access control ———————————————————— #

class TestPantryItemAccess:
	"""Tests for access control and Select helpers."""

	def test_get_InventoryIngredient_by_id_returns_none_for_other_user(self, test_user_id):
		"""Users cannot access another user's pantry item."""
		other_id = create_user("other@test.com", "Other", "pass")
		ingredient_id = get_or_create_ingredient("PrivateItem", test_user_id)
		inv_id = create_inventory_ingredient(1, datetime.utcnow(), None, ingredient_id, None)

		row = Select.get_InventoryIngredient_by_id(inv_id, other_id)
		assert row is None

	def test_get_InventoryIngredients_excludes_deleted(self, test_user_id):
		"""get_InventoryIngredients_by_Persons_id excludes soft-deleted items."""
		ingredient_id = get_or_create_ingredient("Visible", test_user_id)
		create_inventory_ingredient(1, datetime.utcnow(), None, ingredient_id, None)

		ingredient_id2 = get_or_create_ingredient("Deleted", test_user_id)
		inv_id2 = create_inventory_ingredient(1, datetime.utcnow(), None, ingredient_id2, None)
		soft_delete_inventory_ingredient(inv_id2)

		items = Select.get_InventoryIngredients_by_Persons_id(test_user_id)
		names = [ing.name for _, ing in items]
		assert "Visible" in names
		assert "Deleted" not in names
