from sqlalchemy.orm import Session


def get_ListIngredients_by_Persons_id(Persons_id: int):
	"""Return (ListIngredients, Ingredients) tuples for a user's list items."""
	from database import engine, Persons, Ingredients, ListIngredients
	with Session(engine) as session:
		return session.query(ListIngredients, Ingredients).join(
			Ingredients, getattr(ListIngredients, "Ingredients.id") == Ingredients.id
		).filter(getattr(Ingredients, "Persons.id") == Persons_id).all()


def get_InventoryIngredients_by_Persons_id(Persons_id: int):
	"""Return (InventoryIngredients, Ingredients) tuples for a user's pantry items."""
	from database import engine, Ingredients, InventoryIngredients
	with Session(engine) as session:
		return session.query(InventoryIngredients, Ingredients).join(
			Ingredients, getattr(InventoryIngredients, "Ingredients.id") == Ingredients.id
		).filter(
			getattr(Ingredients, "Persons.id") == Persons_id,
			InventoryIngredients.is_deleted == False,
		).all()


def get_InventoryIngredient_by_id(inventory_id: int, Persons_id: int):
	"""Return (InventoryIngredients, Ingredients) for a pantry item if it belongs to the user, else None."""
	from database import engine, Ingredients, InventoryIngredients
	with Session(engine) as session:
		row = session.query(InventoryIngredients, Ingredients).join(
			Ingredients, getattr(InventoryIngredients, "Ingredients.id") == Ingredients.id
		).filter(
			InventoryIngredients.id == inventory_id,
			getattr(Ingredients, "Persons.id") == Persons_id,
			InventoryIngredients.is_deleted == False,
		).first()
		return row


def get_Lists_by_Persons_id(Persons_id: int):
	"""Return all Lists for a user, ordered by name."""
	from database import engine, Lists
	with Session(engine) as session:
		return session.query(Lists).filter(
			getattr(Lists, "Persons.id") == Persons_id
		).order_by(Lists.name).all()


def get_ListIngredients_by_Lists_id(list_id: int, Persons_id: int):
	"""Return (ListIngredients, Ingredients) tuples for a specific list, only if list belongs to user.
	Excludes soft-deleted list ingredients."""
	from database import engine, Persons, Ingredients, ListIngredients, Lists
	with Session(engine) as session:
		return session.query(ListIngredients, Ingredients).join(
			Ingredients, getattr(ListIngredients, "Ingredients.id") == Ingredients.id
		).join(Lists, getattr(ListIngredients, "Lists.id") == Lists.id).filter(
			getattr(Lists, "Persons.id") == Persons_id,
			getattr(ListIngredients, "Lists.id") == list_id,
			ListIngredients.is_deleted == False,
		).all()


def get_ListIngredient_by_id(list_ingredient_id: int, Persons_id: int):
	"""Return (ListIngredients, Ingredients, Lists) for a list item if it belongs to the user, else None."""
	from database import engine, Ingredients, ListIngredients, Lists
	with Session(engine) as session:
		row = session.query(ListIngredients, Ingredients, Lists).join(
			Ingredients, getattr(ListIngredients, "Ingredients.id") == Ingredients.id
		).join(Lists, getattr(ListIngredients, "Lists.id") == Lists.id).filter(
			ListIngredients.id == list_ingredient_id,
			getattr(Lists, "Persons.id") == Persons_id,
			ListIngredients.is_deleted == False,
		).first()
		return row
