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
