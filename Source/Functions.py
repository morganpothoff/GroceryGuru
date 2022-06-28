#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import psycopg2
import werkzeug


# Connects to the database
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
		cursor = connection.cursor()

		try:
			function_result = function(cursor, *args, **kwargs)
			close(cursor, connection)
			return function_result

		except Exception as error:
			close(cursor, connection)
			raise error

	inner.__name__ = function.__name__
	return inner


@connect
def Persons_email_exists(cursor: psycopg2.extensions.cursor, email: str) -> bool:
	"""
	SUMMARY: Checks whether a Persons's email exists.
	PARAMS:  The email to check.
	DETAILS: Makes a query to the DB. Evaluates whether the email exists.
	RETURNS: True is the email is found, false otherwise.
	"""
	cursor.execute("""SELECT * FROM "Persons";""")
	[print(result) for result in cursor]

	cursor.execute("""SELECT * FROM "Persons" WHERE "Email" = %s;""", (email,))
	return cursor.rowcount > 0


@connect
def Persons_username_exists(cursor: psycopg2.extensions.cursor, username: str) -> bool:
	"""
	SUMMARY: Checks whether a Persons's email exists.
	PARAMS:  The email to check.
	DETAILS: Makes a query to the DB. Evaluates whether the email exists.
	RETURNS: True is the email is found, false otherwise.
	"""
	cursor.execute("""SELECT * FROM "Persons" WHERE "Username" = %s;""", (username,))
	return cursor.rowcount > 0


# Adds a new user to the database, returns error message
@connect
def add_new_user(cursor: psycopg2.extensions.cursor, request: werkzeug.local.LocalProxy):
	email: str = request.form["email"]
	if(Persons_email_exists(email)):
		raise Exception(f"There is already an account for email '{email}'.")

	username: str = request.form["uname"]
	if(Persons_username_exists(username)):
		raise Exception(f"There is already an account for username '{username}'.")

	if request.form["pass"] != request.form["confirmPass"]:
		raise Exception("The password and confirmed password do not match. Please try again.")

	query = \
	"""
	INSERT INTO "Persons" ("Email", "Username", "Password")
	  VALUES (%s, %s, %s)
	  RETURNING "PersonID";
	"""
	cursor.execute(query, (email, username, request.form["pass"]))
	print(cursor.statusmessage)

	user_id: int = cursor.fetchone()[0]
	print(user_id)
	#TODO: Get Person Object for user_id
	return user_id
