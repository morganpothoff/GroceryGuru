import os
from sqlalchemy import select
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine


from database import Select


# engine, suppose it has two tables 'user' and 'address' set up
DB_USER = os.getenv("GROCERY_GURU_DB_USER")
DB_PASSWORD = os.getenv("GROCERY_GURU_DB_PASSWORD")
DB_HOST = os.getenv("GROCERY_GURU_DB_HOST")
DB_NAME = os.getenv("GROCERY_GURU_DB_NAME")
engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}")


# reflect the tables
Base = automap_base()
Base.prepare(autoload_with=engine)


# mapped classes are now created with names by default
# matching that of the table name.
Persons = Base.classes.Persons
Lists = Base.classes.Lists
Ingredients = Base.classes.Ingredients
ListIngredients = Base.classes.ListIngredients


def get_user_count():
	with Session(engine) as session:
		return session.query(Persons.id).count()


def create_user(email, name, password):
	test_person = Persons(email=email, name=name, password=password)
	
	with Session(engine) as session:
		session.add(test_person)  # insert
		session.commit()  # commit
		session.refresh(test_person)
		return test_person.id


def create_list(name, Persons_id):
	test_list = Lists(**{"name": name, "Persons.id": Persons_id})

	with Session(engine) as session:
		session.add(test_list)  # insert
		session.commit()  # commit
		session.refresh(test_list)
		return test_list.id


def create_ingredient(name, Persons_id):
	test_ingredient = Ingredients(**{"name": name, "Persons.id": Persons_id})
	
	with Session(engine) as session:
		session.add(test_ingredient)  # insert
		session.commit()  # commit
		session.refresh(test_ingredient)
		return test_ingredient.id


def create_list_ingredient(quantity, date_added, Ingredients_id, Lists_id):
	test_list_ingredient = ListIngredients(**{"quantity": quantity, "date_added": date_added,
				"Ingredients.id": Ingredients_id, "Lists.id": Lists_id})
	
	with Session(engine) as session:
		session.add(test_list_ingredient)  # insert
		session.commit()  # commit
		session.refresh(test_list_ingredient)
		return test_list_ingredient.id
