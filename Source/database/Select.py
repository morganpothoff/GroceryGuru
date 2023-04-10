

from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import TypeVar


ListIngredients = TypeVar("ListIngredients");


def get_ListIngredients_by_Persons_id(Persons_id: int) -> list[ListIngredients]:
	from database import engine, Persons, Ingredients, ListIngredients

	with Session(engine) as session:
		return session.query(ListIngredients, Ingredients) \
			.filter(getattr(ListIngredients, "Ingredients.id") == Ingredients.id) \
			.filter(getattr(Ingredients, "Persons.id") == Persons_id) \
			.all()
