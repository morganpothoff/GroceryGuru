"""Pytest configuration and fixtures for GroceryGuru tests."""
import os
import sys
import shutil
import tempfile
from pathlib import Path

import pytest

# Add Source to path so we can import the app
_project_root = Path(__file__).resolve().parent.parent
_source_dir = _project_root / "Source"
_schema_path = _project_root / "Database" / "schema.sql"
sys.path.insert(0, str(_source_dir))

# Set test env BEFORE importing database/app
os.environ.setdefault("SECRET_KEY", "test-secret-key")
_test_dir = _project_root / "Database" / "_test"
_test_dir.mkdir(parents=True, exist_ok=True)
_test_db_path = str(_test_dir / "grocery.db")
os.environ["GROCERY_GURU_DB_PATH"] = _test_db_path

# Copy schema to test dir so database init can find it
shutil.copy(_schema_path, _test_dir / "schema.sql")


def _copy_schema():
	shutil.copy(_schema_path, _test_dir / "schema.sql")


# Database init looks for schema at parent of db path
# _db_path = _test_dir/grocery.db, so schema at _test_dir/schema.sql (we copied it above)

# Now import - database will use GROCERY_GURU_DB_PATH
# We need to ensure the schema is applied. The db module checks for Persons table.
# If the file doesn't exist, it creates it. Our _test_db_path points to a non-existent
# file in a fresh temp dir. The schema_path in db init will be _test_dir/schema.sql.
# Wait - the database module uses Path(_db_path).parent / "schema.sql". So that's
# _test_dir / "schema.sql". We copied the schema there. Good!

from GroceryGuru import app
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


@pytest.fixture
def client():
	"""Flask test client with test config."""
	app.config["TESTING"] = True
	app.config["SECRET_KEY"] = "test-secret"
	return app.test_client()


@pytest.fixture
def test_user():
	"""Create a test user and return (user_id, email, password)."""
	email = f"pantry_test_{os.getpid()}_{id(object())}@test.com"
	password = "TestPassword123"
	user_id = create_user(email, "Test User", password)
	return (user_id, email, password)


@pytest.fixture
def logged_in_client(client, test_user):
	"""Client with a logged-in user. Returns (client, user_id)."""
	user_id, email, password = test_user
	client.post("/Login", data={"email": email, "pass": password}, follow_redirects=True)
	return (client, user_id)


@pytest.fixture(autouse=True)
def _clean_db_before_test(request):
	"""Clear test database before each test for isolation."""
	import sqlite3
	if _test_db_path and Path(_test_db_path).exists():
		with sqlite3.connect(_test_db_path) as conn:
			try:
				conn.execute("DELETE FROM RecipeImages")
			except sqlite3.OperationalError:
				pass
			try:
				conn.execute("DELETE FROM RecipeRatings")
			except sqlite3.OperationalError:
				pass
			try:
				conn.execute("DELETE FROM RecipeComments")
			except sqlite3.OperationalError:
				pass
			conn.execute("DELETE FROM Recipes")
			conn.execute("DELETE FROM InventoryIngredients")
			conn.execute("DELETE FROM ListIngredients")
			conn.execute("DELETE FROM Ingredients")
			conn.execute("DELETE FROM Lists")
			conn.execute("DELETE FROM Persons")
			conn.commit()
	yield
