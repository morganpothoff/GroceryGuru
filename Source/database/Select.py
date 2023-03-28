

from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import TypeVar


HomeIngredients = TypeVar("HomeIngredients");


def get_HomeIngredients_by_Persons_id(Persons_id: int) -> list[HomeIngredients]:
	from database import add_to_session, engine, Persons, Ingredients, HomeIngredients

	with Session(engine) as session:
		return session.query(HomeIngredients, Ingredients) \
			.filter(getattr(HomeIngredients, "Ingredients.id") == Ingredients.id) \
			.filter(getattr(Ingredients, "Persons.id") == Persons_id) \
			.all()
