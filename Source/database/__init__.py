import os
from pathlib import Path
from werkzeug.security import generate_password_hash
from sqlalchemy import select, insert, update
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine


from database import Select


# SQLite: use env var or default to Database/grocery_guru.db in project root
_db_path = os.getenv("GROCERY_GURU_DB_PATH")
if not _db_path:
	_project_root = Path(__file__).resolve().parent.parent.parent
	_db_path = str(_project_root / "Database" / "grocery_guru.db")
_engine_url = f"sqlite:///{_db_path}"
engine = create_engine(_engine_url, connect_args={"check_same_thread": False})


def _init_schema_if_needed():
	"""Create database file and tables if they don't exist."""
	import sqlite3
	Path(_db_path).parent.mkdir(parents=True, exist_ok=True)
	schema_path = Path(_db_path).parent / "schema.sql"
	if not schema_path.exists():
		return
	with sqlite3.connect(_db_path) as raw:
		cur = raw.execute(
			"SELECT name FROM sqlite_master WHERE type='table' AND name='Persons'"
		)
		if cur.fetchone() is None:
			raw.executescript(schema_path.read_text())


def _migrate_add_notes_if_needed():
	"""Add notes column to InventoryIngredients if it doesn't exist."""
	import sqlite3
	if not Path(_db_path).exists():
		return
	with sqlite3.connect(_db_path) as raw:
		cur = raw.execute("PRAGMA table_info(InventoryIngredients)")
		cols = [row[1] for row in cur.fetchall()]
		if "notes" not in cols:
			raw.execute("ALTER TABLE InventoryIngredients ADD COLUMN notes TEXT")


def _migrate_recipes_table_if_needed():
	"""Create Recipes table if it doesn't exist."""
	import sqlite3
	if not Path(_db_path).exists():
		return
	with sqlite3.connect(_db_path) as raw:
		cur = raw.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Recipes'")
		if cur.fetchone() is None:
			raw.execute("""
				CREATE TABLE "Recipes" (
					"id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
					"title" TEXT NOT NULL,
					"ingredients" TEXT NOT NULL DEFAULT '',
					"steps" TEXT NOT NULL DEFAULT '',
					"special_notes" TEXT DEFAULT '',
					"source_url" TEXT,
					"category" TEXT DEFAULT '',
					"image_url" TEXT,
					"Persons.id" INTEGER NOT NULL,
					"is_deleted" INTEGER NOT NULL DEFAULT 0,
					"date_added" TEXT NOT NULL DEFAULT (datetime('now')),
					FOREIGN KEY ("Persons.id") REFERENCES "Persons"("id")
				)
			""")


def _migrate_recipes_image_url_if_needed():
	"""Add image_url column to Recipes if it doesn't exist."""
	import sqlite3
	if not Path(_db_path).exists():
		return
	with sqlite3.connect(_db_path) as raw:
		cur = raw.execute("PRAGMA table_info(Recipes)")
		cols = [row[1] for row in cur.fetchall()]
		if "image_url" not in cols:
			raw.execute("ALTER TABLE Recipes ADD COLUMN image_url TEXT")


def _migrate_recipe_ratings_if_needed():
	"""Create RecipeRatings table if it doesn't exist."""
	import sqlite3
	if not Path(_db_path).exists():
		return
	with sqlite3.connect(_db_path) as raw:
		cur = raw.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='RecipeRatings'")
		if cur.fetchone() is None:
			raw.execute("""
				CREATE TABLE "RecipeRatings" (
					"id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
					"Recipes.id" INTEGER NOT NULL,
					"Persons.id" INTEGER NOT NULL,
					"rating" INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
					"created_at" TEXT NOT NULL DEFAULT (datetime('now')),
					UNIQUE ("Recipes.id", "Persons.id"),
					FOREIGN KEY ("Recipes.id") REFERENCES "Recipes"("id"),
					FOREIGN KEY ("Persons.id") REFERENCES "Persons"("id")
				)
			""")


def _migrate_recipe_comments_if_needed():
	"""Create RecipeComments table if it doesn't exist."""
	import sqlite3
	if not Path(_db_path).exists():
		return
	with sqlite3.connect(_db_path) as raw:
		cur = raw.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='RecipeComments'")
		if cur.fetchone() is None:
			raw.execute("""
				CREATE TABLE "RecipeComments" (
					"id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
					"Recipes.id" INTEGER NOT NULL,
					"Persons.id" INTEGER NOT NULL,
					"body" TEXT NOT NULL,
					"created_at" TEXT NOT NULL DEFAULT (datetime('now')),
					FOREIGN KEY ("Recipes.id") REFERENCES "Recipes"("id"),
					FOREIGN KEY ("Persons.id") REFERENCES "Persons"("id")
				)
			""")


def _migrate_recipe_images_if_needed():
	"""Create RecipeImages table for multiple images per recipe."""
	import sqlite3
	if not Path(_db_path).exists():
		return
	with sqlite3.connect(_db_path) as raw:
		cur = raw.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='RecipeImages'")
		if cur.fetchone() is None:
			raw.execute("""
				CREATE TABLE "RecipeImages" (
					"id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
					"Recipes.id" INTEGER NOT NULL,
					"file_path" TEXT NOT NULL,
					"sort_order" INTEGER NOT NULL DEFAULT 0,
					FOREIGN KEY ("Recipes.id") REFERENCES "Recipes"("id")
				)
			""")


_init_schema_if_needed()
_migrate_add_notes_if_needed()
_migrate_recipes_table_if_needed()
_migrate_recipes_image_url_if_needed()
_migrate_recipe_ratings_if_needed()
_migrate_recipe_comments_if_needed()
_migrate_recipe_images_if_needed()

# reflect the tables
Base = automap_base()
Base.prepare(autoload_with=engine)


# mapped classes are now created with names by default
# matching that of the table name.
Persons = Base.classes.Persons
Lists = Base.classes.Lists
Ingredients = Base.classes.Ingredients
ListIngredients = Base.classes.ListIngredients
InventoryIngredients = Base.classes.InventoryIngredients
Recipes = Base.classes.Recipes
RecipeRatings = Base.classes.RecipeRatings
RecipeComments = Base.classes.RecipeComments
RecipeImages = Base.classes.RecipeImages


def get_user_count():
	with Session(engine) as session:
		return session.query(Persons.id).count()


def create_user(email, name, password):
	password_hash = generate_password_hash(password, method="pbkdf2:sha256")
	test_person = Persons(email=email, name=name, password=password_hash)
	
	with Session(engine) as session:
		session.add(test_person)  # insert
		session.commit()  # commit
		session.refresh(test_person)
		return test_person.id


def create_list(name, Persons_id):
	# Use Core insert: SQLAlchemy ORM forbids **kwargs with dotted column names like "Persons.id"
	with Session(engine) as session:
		stmt = insert(Lists.__table__).values(**{"name": name, "Persons.id": Persons_id})
		result = session.execute(stmt)
		session.commit()
		return result.inserted_primary_key[0]


def create_ingredient(name, Persons_id):
	with Session(engine) as session:
		stmt = insert(Ingredients.__table__).values(**{"name": name, "Persons.id": Persons_id})
		result = session.execute(stmt)
		session.commit()
		return result.inserted_primary_key[0]


def create_list_ingredient(quantity, date_added, Ingredients_id, Lists_id):
	with Session(engine) as session:
		stmt = insert(ListIngredients.__table__).values(**{
			"quantity": quantity,
			"date_added": date_added,
			"Ingredients.id": Ingredients_id,
			"Lists.id": Lists_id,
		})
		result = session.execute(stmt)
		session.commit()
		return result.inserted_primary_key[0]


def get_or_create_list(name: str, Persons_id: int) -> int:
	"""Get first list by name for user, or create it. Returns list id."""
	with Session(engine) as session:
		stmt = select(Lists).where(
			getattr(Lists, "Persons.id") == Persons_id,
			Lists.name == name,
		)
		row = session.execute(stmt).scalars().first()
		if row:
			return row.id
		return create_list(name, Persons_id)


def get_or_create_ingredient(name: str, Persons_id: int) -> int:
	"""Get first non-deleted ingredient by name for user, or create it. Returns ingredient id."""
	with Session(engine) as session:
		stmt = select(Ingredients).where(
			getattr(Ingredients, "Persons.id") == Persons_id,
			Ingredients.name == name,
			Ingredients.is_deleted == False,
		)
		row = session.execute(stmt).scalars().first()
		if row:
			return row.id
		return create_ingredient(name, Persons_id)


def create_inventory_ingredient(count: int, date_purchased, date_expires, Ingredients_id: int, ListIngredients_id=None):
	"""Add an item to the user's pantry (inventory)."""
	with Session(engine) as session:
		values = {
			"count": count,
			"date_purchased": date_purchased,
			"date_expires": date_expires if date_expires else None,
			"Ingredients.id": Ingredients_id,
			"ListIngredients.id": ListIngredients_id,
			"is_deleted": False,
		}
		stmt = insert(InventoryIngredients.__table__).values(**values)
		result = session.execute(stmt)
		session.commit()
		return result.inserted_primary_key[0]


def _norm_expires(val):
	"""Normalize date_expires to YYYY-MM-DD string or None for comparison."""
	if val is None:
		return None
	if hasattr(val, "strftime"):
		return val.strftime("%Y-%m-%d")
	s = str(val)
	return s[:10] if len(s) >= 10 else s


def find_matching_inventory_item(Ingredients_id: int, date_expires) -> int | None:
	"""Find an existing non-deleted pantry item with same ingredient and matching expiration.
	Returns the inventory item id if found, else None.
	Match: both have no expiration, or both have the same expiration date.
	"""
	norm_new = _norm_expires(date_expires)
	with Session(engine) as session:
		stmt = select(InventoryIngredients).where(
			getattr(InventoryIngredients, "Ingredients.id") == Ingredients_id,
			InventoryIngredients.is_deleted == False,
		)
		for inv in session.scalars(stmt):
			norm_existing = _norm_expires(getattr(inv, "date_expires", None))
			if norm_existing == norm_new:
				return inv.id
	return None


def add_inventory_count(inventory_id: int, add_count: int):
	"""Add add_count to the existing inventory item's count."""
	tbl = InventoryIngredients.__table__
	with Session(engine) as session:
		stmt = (
			update(tbl)
			.where(tbl.c.id == inventory_id)
			.values(count=tbl.c.count + add_count)
		)
		session.execute(stmt)
		session.commit()


def update_inventory_ingredient(inventory_id: int, count: int, date_expires=None, notes: str = None):
	"""Update an inventory item's fields. Pass None for date_expires or notes to clear them."""
	tbl = InventoryIngredients.__table__
	values = {
		"count": max(1, count),
		"date_expires": date_expires,
		"notes": (notes or "").strip() or None,
	}
	col_names = {c.name for c in tbl.c}
	values = {k: v for k, v in values.items() if k in col_names}
	with Session(engine) as session:
		stmt = update(tbl).where(tbl.c.id == inventory_id).values(**values)
		session.execute(stmt)
		session.commit()


def soft_delete_inventory_ingredient(inventory_id: int):
	"""Soft-delete an inventory item by setting is_deleted=True."""
	tbl = InventoryIngredients.__table__
	with Session(engine) as session:
		stmt = update(tbl).where(tbl.c.id == inventory_id).values(is_deleted=True)
		session.execute(stmt)
		session.commit()


def update_list_ingredient(list_ingredient_id: int, quantity: int):
	"""Update a list item's quantity."""
	tbl = ListIngredients.__table__
	with Session(engine) as session:
		stmt = update(tbl).where(tbl.c.id == list_ingredient_id).values(quantity=max(1, quantity))
		session.execute(stmt)
		session.commit()


def soft_delete_list_ingredient(list_ingredient_id: int):
	"""Soft-delete a list item by setting is_deleted=True."""
	tbl = ListIngredients.__table__
	with Session(engine) as session:
		stmt = update(tbl).where(tbl.c.id == list_ingredient_id).values(is_deleted=True)
		session.execute(stmt)
		session.commit()


# ————————————————————————————————— Recipes ———————————————————————————————— #

def create_recipe(title: str, Persons_id: int, ingredients: str = "", steps: str = "", special_notes: str = None, source_url: str = None, category: str = None, image_url: str = None):
	"""Create a new recipe."""
	with Session(engine) as session:
		values = {
			"title": title,
			"ingredients": ingredients or "",
			"steps": steps or "",
			"special_notes": (special_notes or "").strip() or None,
			"source_url": (source_url or "").strip() or None,
			"category": (category or "").strip() or None,
			"Persons.id": Persons_id,
		}
		if hasattr(Recipes.__table__.c, "image_url"):
			values["image_url"] = (image_url or "").strip() or None
		stmt = insert(Recipes.__table__).values(**values)
		result = session.execute(stmt)
		session.commit()
		return result.inserted_primary_key[0]


def update_recipe(recipe_id: int, title: str = None, ingredients: str = None, steps: str = None, special_notes: str = None, source_url: str = None, category: str = None, image_url: str = None):
	"""Update recipe fields. Pass None to leave unchanged."""
	tbl = Recipes.__table__
	updates = {}
	if title is not None:
		updates["title"] = title
	if ingredients is not None:
		updates["ingredients"] = ingredients
	if steps is not None:
		updates["steps"] = steps
	if special_notes is not None:
		updates["special_notes"] = (special_notes or "").strip() or None
	if source_url is not None:
		updates["source_url"] = (source_url or "").strip() or None
	if category is not None:
		updates["category"] = (category or "").strip() or None
	if image_url is not None and hasattr(tbl.c, "image_url"):
		updates["image_url"] = (image_url or "").strip() or None
	if not updates:
		return
	with Session(engine) as session:
		stmt = update(tbl).where(tbl.c.id == recipe_id).values(**updates)
		session.execute(stmt)
		session.commit()


def soft_delete_recipe(recipe_id: int):
	"""Soft-delete a recipe."""
	tbl = Recipes.__table__
	with Session(engine) as session:
		stmt = update(tbl).where(tbl.c.id == recipe_id).values(is_deleted=True)
		session.execute(stmt)
		session.commit()


def upsert_recipe_rating(recipe_id: int, Persons_id: int, rating: int):
	"""Set or update a user's rating (1-5) for a recipe. Uses INSERT OR REPLACE for SQLite."""
	rating = max(1, min(5, int(rating)))
	with Session(engine) as session:
		existing = session.execute(
			select(RecipeRatings).where(
				getattr(RecipeRatings, "Recipes.id") == recipe_id,
				getattr(RecipeRatings, "Persons.id") == Persons_id,
			)
		).scalar_one_or_none()
		if existing:
			session.execute(
				update(RecipeRatings.__table__)
				.where(getattr(RecipeRatings.__table__.c, "id") == existing.id)
				.values(rating=rating)
			)
		else:
			session.execute(
				insert(RecipeRatings.__table__).values(**{
					"Recipes.id": recipe_id,
					"Persons.id": Persons_id,
					"rating": rating,
				})
			)
		session.commit()


def create_recipe_comment(recipe_id: int, Persons_id: int, body: str) -> int:
	"""Add a comment to a recipe. Returns comment id."""
	body = (body or "").strip()
	if not body:
		raise ValueError("Comment body cannot be empty")
	with Session(engine) as session:
		stmt = insert(RecipeComments.__table__).values(**{
			"Recipes.id": recipe_id,
			"Persons.id": Persons_id,
			"body": body,
		})
		result = session.execute(stmt)
		session.commit()
		return result.inserted_primary_key[0]


def create_recipe_image(recipe_id: int, file_path: str) -> int:
	"""Add an image to a recipe. file_path is relative to static (e.g. uploads/recipes/xxx.jpg). Returns image id."""
	with Session(engine) as session:
		# Get max sort_order
		from sqlalchemy import func
		result = session.query(func.coalesce(func.max(RecipeImages.sort_order), -1)).filter(
			getattr(RecipeImages, "Recipes.id") == recipe_id,
		).scalar()
		max_order = -1 if result is None else result
		stmt = insert(RecipeImages.__table__).values(**{
			"Recipes.id": recipe_id,
			"file_path": file_path,
			"sort_order": max_order + 1,
		})
		result = session.execute(stmt)
		session.commit()
		return result.inserted_primary_key[0]


def delete_recipe_image(recipe_id: int, image_id: int) -> bool:
	"""Delete a recipe image. Returns True if deleted, False if not found or not owned."""
	from sqlalchemy import delete as sql_delete
	tbl = RecipeImages.__table__
	with Session(engine) as session:
		row = session.query(RecipeImages).filter(
			RecipeImages.id == image_id,
			getattr(RecipeImages, "Recipes.id") == recipe_id,
		).first()
		if not row:
			return False
		file_path = row.file_path
		session.execute(sql_delete(tbl).where(tbl.c.id == image_id))
		session.commit()
	# Remove file from disk
	full_path = Path(__file__).resolve().parent / "static" / file_path
	if full_path.exists():
		try:
			full_path.unlink()
		except OSError:
			pass
	return True
