"""Unit tests for adding, editing, and deleting list items (shopping list items)."""
from datetime import datetime

import pytest

from database import (
	create_user,
	create_list,
	create_list_ingredient,
	get_or_create_list,
	get_or_create_ingredient,
	update_list_ingredient,
	soft_delete_list_ingredient,
)
from database import Select


# ————————————————————————————————— Fixtures ————————————————————————————————— #

@pytest.fixture
def test_user_id():
	"""Create a test user and return user_id."""
	email = f"list_{id(object())}@test.com"
	user_id = create_user(email, "Test User", "TestPass123")
	return user_id


@pytest.fixture
def test_list(test_user_id):
	"""Create a test list and return (list_id, list_name)."""
	list_id = get_or_create_list("Grocery list", test_user_id)
	return (list_id, "Grocery list")


# ————————————————————————————————— Add list item ——————————————————————————— #

class TestAddListItem:
	"""Tests for adding items to shopping lists."""

	def test_add_list_item_route(self, logged_in_client):
		"""POST /AddListItem adds item to specified list."""
		client, user_id = logged_in_client
		resp = client.post(
			"/AddListItem",
			data={
				"destination": "Grocery list",
				"item_name": "Milk",
				"quantity": "3",
			},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=True,
		)
		assert resp.status_code == 200

		lists = Select.get_Lists_by_Persons_id(user_id)
		assert len(lists) >= 1
		grocery = next((l for l in lists if l.name == "Grocery list"), None)
		assert grocery is not None

		items = Select.get_ListIngredients_by_Lists_id(grocery.id, user_id)
		assert len(items) == 1
		list_ing, ingredient = items[0]
		assert ingredient.name == "Milk"
		assert list_ing.quantity == 3

	def test_add_list_item_creates_custom_list(self, logged_in_client):
		"""Adding to a new list name creates the list."""
		client, user_id = logged_in_client
		resp = client.post(
			"/AddListItem",
			data={
				"destination": "Birthday Party Shopping",
				"item_name": "Cake mix",
				"quantity": "1",
			},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=True,
		)
		assert resp.status_code == 200

		lists = Select.get_Lists_by_Persons_id(user_id)
		party_list = next((l for l in lists if l.name == "Birthday Party Shopping"), None)
		assert party_list is not None

		items = Select.get_ListIngredients_by_Lists_id(party_list.id, user_id)
		assert len(items) == 1
		assert items[0][1].name == "Cake mix"

	def test_add_list_item_requires_item_name(self, logged_in_client):
		"""POST /AddListItem returns error when item_name is empty."""
		client, _ = logged_in_client
		resp = client.post(
			"/AddListItem",
			data={
				"destination": "Grocery list",
				"item_name": "",
				"quantity": "1",
			},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=False,
		)
		assert resp.status_code == 200  # Renders form with error
		assert b"required" in resp.data.lower() or b"name" in resp.data.lower()

	def test_create_list_ingredient_db(self, test_user_id, test_list):
		"""Database: create_list_ingredient inserts a new row."""
		list_id, _ = test_list
		ingredient_id = get_or_create_ingredient("Bananas", test_user_id)

		li_id = create_list_ingredient(
			quantity=5,
			date_added=datetime.utcnow(),
			Ingredients_id=ingredient_id,
			Lists_id=list_id,
		)
		assert li_id is not None

		row = Select.get_ListIngredient_by_id(li_id, test_user_id)
		assert row is not None
		list_ing, ingredient, lst = row
		assert ingredient.name == "Bananas"
		assert list_ing.quantity == 5


# ————————————————————————————————— Edit list item —————————————————————————— #

class TestEditListItem:
	"""Tests for editing list items."""

	def test_update_list_item_via_list_item_route(self, logged_in_client):
		"""POST to ListItem with action=update saves quantity."""
		client, user_id = logged_in_client
		list_id = get_or_create_list("Grocery list", user_id)
		ingredient_id = get_or_create_ingredient("Apples", user_id)
		li_id = create_list_ingredient(2, datetime.utcnow(), ingredient_id, list_id)

		resp = client.post(
			f"/ListItem/{li_id}",
			data={"action": "update", "quantity": "7"},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=True,
		)
		assert resp.status_code == 200

		row = Select.get_ListIngredient_by_id(li_id, user_id)
		assert row is not None
		list_ing, ingredient, lst = row
		assert list_ing.quantity == 7
		assert ingredient.name == "Apples"

	def test_update_list_ingredient_db(self, test_user_id, test_list):
		"""Database: update_list_ingredient updates quantity."""
		list_id, _ = test_list
		ingredient_id = get_or_create_ingredient("Oranges", test_user_id)
		li_id = create_list_ingredient(1, datetime.utcnow(), ingredient_id, list_id)

		update_list_ingredient(li_id, quantity=12)

		row = Select.get_ListIngredient_by_id(li_id, test_user_id)
		assert row is not None
		assert row[0].quantity == 12

	def test_update_list_ingredient_enforces_min_quantity(self, test_user_id, test_list):
		"""update_list_ingredient clamps quantity to at least 1."""
		list_id, _ = test_list
		ingredient_id = get_or_create_ingredient("Lemons", test_user_id)
		li_id = create_list_ingredient(5, datetime.utcnow(), ingredient_id, list_id)

		update_list_ingredient(li_id, quantity=0)

		row = Select.get_ListIngredient_by_id(li_id, test_user_id)
		assert row is not None
		assert row[0].quantity == 1

	def test_list_item_requires_login(self, client):
		"""GET /ListItem/<id> redirects to login when not authenticated."""
		resp = client.get("/ListItem/1", follow_redirects=False)
		assert resp.status_code in (302, 401)
		if resp.status_code == 302:
			assert "Login" in resp.headers.get("Location", "")


# ————————————————————————————————— Delete list item ————————————————————————— #

class TestDeleteListItem:
	"""Tests for deleting list items."""

	def test_delete_list_item_via_action(self, logged_in_client):
		"""POST to ListItem with action=delete soft-deletes item."""
		client, user_id = logged_in_client
		list_id = get_or_create_list("Grocery list", user_id)
		ingredient_id = get_or_create_ingredient("RemoveMe", user_id)
		li_id = create_list_ingredient(1, datetime.utcnow(), ingredient_id, list_id)

		resp = client.post(
			f"/ListItem/{li_id}",
			data={"action": "delete"},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=True,
		)
		assert resp.status_code == 200

		row = Select.get_ListIngredient_by_id(li_id, user_id)
		assert row is None

		items = Select.get_ListIngredients_by_Lists_id(list_id, user_id)
		assert len(items) == 0

	def test_delete_list_item_route(self, logged_in_client):
		"""POST /DeleteListItem/<id> soft-deletes and redirects."""
		client, user_id = logged_in_client
		list_id = get_or_create_list("Test list", user_id)
		ingredient_id = get_or_create_ingredient("ToDelete", user_id)
		li_id = create_list_ingredient(1, datetime.utcnow(), ingredient_id, list_id)

		lists = Select.get_Lists_by_Persons_id(user_id)
		test_list = next((l for l in lists if l.name == "Test list"), None)
		assert test_list is not None

		resp = client.post(
			f"/DeleteListItem/{li_id}",
			data={"redirect_to": f"/ShoppingList/{user_id}/Test%20list"},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=True,
		)
		assert resp.status_code == 200

		row = Select.get_ListIngredient_by_id(li_id, user_id)
		assert row is None

	def test_delete_nonexistent_list_item_returns_404(self, logged_in_client):
		"""POST /DeleteListItem/99999 returns 404 for non-existent item."""
		client, _ = logged_in_client
		resp = client.post(
			"/DeleteListItem/99999",
			data={},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=False,
		)
		assert resp.status_code == 404

	def test_soft_delete_list_ingredient_db(self, test_user_id, test_list):
		"""Database: soft_delete_list_ingredient sets is_deleted=True."""
		list_id, _ = test_list
		ingredient_id = get_or_create_ingredient("SoftDeleteTest", test_user_id)
		li_id = create_list_ingredient(1, datetime.utcnow(), ingredient_id, list_id)

		soft_delete_list_ingredient(li_id)

		row = Select.get_ListIngredient_by_id(li_id, test_user_id)
		assert row is None

	def test_cannot_access_deleted_list_item(self, logged_in_client):
		"""GET /ListItem/<id> returns 404 for soft-deleted item."""
		client, user_id = logged_in_client
		list_id = get_or_create_list("Grocery list", user_id)
		ingredient_id = get_or_create_ingredient("DeletedItem", user_id)
		li_id = create_list_ingredient(1, datetime.utcnow(), ingredient_id, list_id)

		soft_delete_list_ingredient(li_id)

		resp = client.get(f"/ListItem/{li_id}", follow_redirects=False)
		assert resp.status_code == 404


# ————————————————————————————————— Select / access control —————————————————— #

class TestListItemAccess:
	"""Tests for access control and Select helpers."""

	def test_get_ListIngredient_by_id_returns_none_for_other_user(self, test_user_id, test_list):
		"""Users cannot access another user's list item."""
		other_id = create_user("other_list@test.com", "Other", "pass")
		list_id, _ = test_list
		ingredient_id = get_or_create_ingredient("PrivateItem", test_user_id)
		li_id = create_list_ingredient(1, datetime.utcnow(), ingredient_id, list_id)

		row = Select.get_ListIngredient_by_id(li_id, other_id)
		assert row is None

	def test_get_ListIngredients_excludes_deleted(self, test_user_id, test_list):
		"""get_ListIngredients_by_Lists_id excludes soft-deleted items."""
		list_id, _ = test_list
		ingredient_id = get_or_create_ingredient("Visible", test_user_id)
		create_list_ingredient(1, datetime.utcnow(), ingredient_id, list_id)

		ingredient_id2 = get_or_create_ingredient("Deleted", test_user_id)
		li_id2 = create_list_ingredient(1, datetime.utcnow(), ingredient_id2, list_id)
		soft_delete_list_ingredient(li_id2)

		items = Select.get_ListIngredients_by_Lists_id(list_id, test_user_id)
		names = [ing.name for _, ing in items]
		assert "Visible" in names
		assert "Deleted" not in names
