#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from User import User
from werkzeug.security import generate_password_hash, check_password_hash

import os
import sqlite3


# ————————————————————————————————————————————————————— Database ————————————————————————————————————————————————————— #

def _get_db_path():
	"""Get SQLite database path from env or default."""
	path = os.getenv("GROCERY_GURU_DB_PATH")
	if path:
		return path
	from pathlib import Path
	project_root = Path(__file__).resolve().parent.parent
	return str(project_root / "Database" / "grocery_guru.db")


def close(*connections) -> None:
	"""Closes all passed connections/cursors."""
	for obj in connections:
		obj.close()


def connect(function: callable) -> callable:
	"""
	Wraps functions to create a SQLite connection, pass a dict cursor, and close when done.
	"""

	def inner(*args, **kwargs):
		connection = sqlite3.connect(_get_db_path())
		connection.row_factory = sqlite3.Row  # dict-like access via row["col"]
		cursor = connection.cursor()

		try:
			result = function(cursor, *args, **kwargs)
			connection.commit()
			close(cursor, connection)
			return result
		except Exception as error:
			connection.rollback()
			close(cursor, connection)
			raise error

	inner.__name__ = function.__name__
	return inner


# ————————————————————————————————————————————————— Users/Logging In ————————————————————————————————————————————————— #

@connect
def Persons_email_exists(cursor, email: str) -> bool:
	"""Checks whether a Persons's email exists."""
	cursor.execute('SELECT 1 FROM "Persons" WHERE "email" = ?;', (email,))
	return cursor.fetchone() is not None


@connect
def get_user_by_id(cursor, user_id):
	query = 'SELECT * FROM "Persons" WHERE "id" = ?;'
	cursor.execute(query, (user_id,))
	user_info = cursor.fetchone()

	if user_info is None:
		raise Exception("This account does not exist.")

	user_info = dict(user_info)
	current_user = User(
		user_info["id"], user_info["email"], user_info["name"], user_info["password"]
	)
	return current_user


@connect
def add_new_user(cursor, request):
	"""Attempts to add a new user to the database."""
	email = request.form["email"]
	if Persons_email_exists(email):
		raise Exception(f"There is already an account for email '{email}'.")

	if request.form["pass"] != request.form["confirmPass"]:
		raise Exception("The password and confirmed password do not match. Please try again.")

	password_hash = generate_password_hash(request.form["pass"], method="pbkdf2:sha256")
	query = '''
		INSERT INTO "Persons" ("email", "name", "password") VALUES (?, ?, ?);
	'''
	cursor.execute(query, (email, request.form["name"], password_hash))
	user_id = cursor.lastrowid

	if not user_id:
		raise Exception("DB Error while attempting to add new user to DB")

	cursor.execute('SELECT * FROM "Persons" WHERE "id" = ?;', (user_id,))
	user_info = dict(cursor.fetchone())
	current_user = User(
		user_info["id"], user_info["email"], user_info["name"], user_info["password"]
	)
	return current_user


def _verify_password(stored_hash: str, password: str) -> bool:
	"""Verify a password against a stored hash."""
	return check_password_hash(stored_hash, password)


@connect
def login_user(cursor, request):
	"""Attempts to login user to the website."""
	query = 'SELECT * FROM "Persons" WHERE "email" = ?;'
	cursor.execute(query, (request.form["email"],))
	user_info = cursor.fetchone()

	if user_info is None:
		raise Exception("This email does not exist. Please try again.")

	user_info = dict(user_info)
	if not _verify_password(user_info["password"], request.form["pass"]):
		raise Exception("The entered password does not match the email. Please try again.")

	current_user = User(
		user_info["id"], user_info["email"], user_info["name"], user_info["password"]
	)
	return current_user
