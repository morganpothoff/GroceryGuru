#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from User import User

import os
import psycopg2
import psycopg2.extras
import werkzeug


# ————————————————————————————————————————————————————— Database ————————————————————————————————————————————————————— #

def close(*connections: list) -> None:
	"""
	SUMMARY: Closes all passed connections.
	DETAILS: Iterates through connections, calling the close method on each connection.
	"""
	
	for connection in connections:
		connection.close()


def connect(function: callable) -> callable:
	"""
	SUMMARY: Wraps functions with function to create cursor for DB and close connections when done it.
	DETAILS: Gets the environment variable for the DB's connection. Connects to the Postgresql DB. Creates a cursor for
	         the connection. Passes it to the callback. Closes connection to DB.
	RETURNS: The wrapped function with the cursor for the established connection.
	"""
	
	def inner(*args: list, **kwargs: dict) -> callable:
		DB_USER = os.getenv("GROCERY_GURU_DB_USER")
		DB_PASSWORD = os.getenv("GROCERY_GURU_DB_PASSWORD")
		assert(DB_USER is not None), "'DB_USER' not set"
		assert(DB_PASSWORD is not None), "'DB_PASSWORD' not set"
		connection_string = f"host=localhost dbname=GroceryGuru user={DB_USER} password={DB_PASSWORD}"

		connection = psycopg2.connect(connection_string)
		connection.autocommit = True  # Automatically commit changes to DB
		cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

		try:
			function_result = function(cursor, *args, **kwargs)
			close(cursor, connection)
			return function_result

		except Exception as error:
			close(cursor, connection)
			raise error

	inner.__name__ = function.__name__
	return inner



# ————————————————————————————————————————————————— Users/Logging In ————————————————————————————————————————————————— #

@connect
def Persons_email_exists(cursor: psycopg2.extensions.cursor, email: str) -> bool:
	"""
	SUMMARY: Checks whether a Persons's email exists.
	PARAMS:  The email to check.
	DETAILS: Makes a query to the DB. Evaluates whether the email exists.
	RETURNS: True is the email is found, false otherwise.
	"""
	
	cursor.execute("""SELECT * FROM "Persons" WHERE "email" = %s;""", (email,))
	return cursor.rowcount > 0


@connect
def get_user_by_id(cursor: psycopg2.extensions.cursor, user_id):
	query = \
	"""
	SELECT *
	FROM "Persons"
	WHERE "id" = %s;
	"""
	cursor.execute(query, (user_id,))
	user_info = cursor.fetchone()

	if(user_info is None):
		raise Exception(f"This account does not exist.")

	current_user = User(user_info["id"], user_info["email"], user_info["name"], user_info["password"])
	return current_user


@connect
def add_new_user(cursor: psycopg2.extensions.cursor, request: werkzeug.local.LocalProxy):
	"""
	SUMMARY: Attempts to add a new user to the database.
	PARAMS:  The request to be handled.
	DETAILS: Makes a query to the DB. Evaluates whether the email/username exists. Inserts new user.
	RETURNS: Exception raised, dict user_info otherwise.
	"""
	
	email: str = request.form["email"]
	if(Persons_email_exists(email)):
		raise Exception(f"There is already an account for email '{email}'.")

	if(request.form["pass"] != request.form["confirmPass"]):
		raise Exception("The password and confirmed password do not match. Please try again.")

	query = \
	"""
	INSERT INTO "Persons" ("email", "name", "password")
	  VALUES (%s, %s, %s)
	  RETURNING *;
	"""
	cursor.execute(query, (email, request.form["name"], request.form["pass"]))
	print(cursor.statusmessage)

	user_info: dict = cursor.fetchone()
	if(not user_info):
		raise Exception("DB Error while attempting to add new user to DB")

	current_user = User(user_info["id"], user_info["email"], user_info["name"], user_info["password"])
	return current_user


@connect
def login_user(cursor: psycopg2.extensions.cursor, request: werkzeug.local.LocalProxy):
	"""
	SUMMARY: Attempts to login user to the website.
	PARAMS:  The request to be handled.
	DETAILS: Makes a query to the DB. Raises exception if no user found or username and password do not match, 
	         otherwise logs user into website.
	RETURNS: Exception raised, dict user_info otherwise.
	"""
	
	query = \
	"""
	SELECT *
	FROM "Persons"
	WHERE "email" = %s;
	"""
	cursor.execute(query, (request.form["email"],))
	user_info = cursor.fetchone()
	print(user_info)

	if(user_info is None):
		raise Exception(f"This email does not exist. Please try again.")

	if((user_info := dict(user_info))["password"] != request.form["pass"]):
		raise Exception(f"The entered password does not match the email. Please try again.")
	
	current_user = User(user_info["id"], user_info["email"], user_info["name"], user_info["password"])
	return current_user





