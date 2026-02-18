import os
from pathlib import Path
from werkzeug.security import generate_password_hash
from sqlalchemy import select, insert
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


_init_schema_if_needed()

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
