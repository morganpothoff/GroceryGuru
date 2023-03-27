import os
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine


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
Ingredients = Base.classes.Ingredients


def create_user():
	test_person = Persons(email="test.user@email.com", name="TestUser", password="TestUserPassword")
	with Session(engine) as session:
		session.add(test_person)  # insert
		session.commit()  # commit


def create_ingredient():
	test_ingredient = Ingredients(**{"item_name": "Bananas", "brand_name": "Dole", "Persons.id": 1})
	with Session(engine) as session:
		session.add(test_ingredient)  # insert
		session.commit()  # commit
