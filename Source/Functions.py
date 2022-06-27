#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from flask import *
from datetime import datetime
import database.DatabaseConnection
import json
import os
import psycopg2


# Connects to the database
def new_database_connection():
	DB_USER = os.getenv("GROCERY_GURU_DB_USER")
	DB_PASSWORD = os.getenv("GROCERY_GURU_DB_PASSWORD")
	connection = psycopg2.connect(F"host=localhost dbname=GroceryGuru user={DB_USER} password={DB_PASSWORD}")
	return connection


# Determines if user exists from email or uname
def user_exists(request):
	connection = new_database_connection()
	connection.autocommit = True	# Set auto commit to false
	cursor = connection.cursor()
	
	cursor.execute("""SELECT * FROM "Persons" WHERE "Email" = %s;""", (request.form["email"],))
	number_of_results_with_matching_Email = cursor.rowcount
	if number_of_results_with_matching_Email > 0:
		return True

	cursor.execute("""SELECT * FROM "Persons" WHERE "Username" = %s;""", (request.form["uname"],))
	number_of_results_with_matching_Username = cursor.rowcount
	if number_of_results_with_matching_Email > 0:
		return True

	connection.commit()
	cursor.close()
	connection.close()
	return False


# Adds a new user to the database, returns error message
def add_new_user(request):
	connection = new_database_connection()
	connection.autocommit = True	# Set auto commit to false
	cursor = connection.cursor()

	# Email and username already exist together in database
	if user_exists(request):
		return "There is already an account with this email and username. Please change one to create a new account."

	# Password and confirmed password do not match
	if request.form["pass"] != request.form["confirmPass"]:
		return "The password and confirmed password do not match. Please try again."

	cursor.execute("""INSERT INTO "Persons"("Email", "Username", "Password") VALUES (%s, %s, %s);""",
		(request.form["email"], request.form["uname"], request.form["pass"]))

	connection.commit()
	cursor.close()
	connection.close()

	user_id = cursor.fetchone()[0]
	return None
