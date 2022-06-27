#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from flask import *
from datetime import datetime
import database.DatabaseConnection
import json
import os
import psycopg2
import Functions
#import DB_Connections


app = Flask(__name__, static_url_path="/static")


######################### Pre Login #########################
@app.route("/")
def openingHome():
	return render_template("OpeningHome.html")


@app.route("/Login", methods=["GET", "POST"])
def login():
	error = None
	if request.method == "POST":
		if request.form["uname"] != "admin" or request.form["pass"] != "admin":
			error = "Invalid Credentials. Please try again."
		else:
			return redirect(url_for("home"))
	return render_template("Login.html", error=error)


@app.route("/ResetPassword")
def resetPassword():
	return render_template("ResetPassword.html")


@app.route("/CreateAccount", methods=["GET", "POST"])
def createAccount():
	if request.method == "POST":
		Functions.add_new_user(request)
		return render_template("Home.html")		# Set logged in user to new username
	else:
		return render_template("CreateAccount.html")



######################## Post Login #########################
   ######################## Lists ########################
@app.route("/Home")
def home():
	return render_template("Home.html")


@app.route("/MyPantry")
def myPantry():
	return render_template("MyPantry.html")


@app.route("/MyFridge")
def myFridge():
	return render_template("MyFridge.html")


@app.route("/MySpices")
def mySpices():
	return render_template("MySpices.html")


@app.route("/MyTools")
def myTools():
	return render_template("MyTools.html")


@app.route("/Recipes")
def recipes():
	return render_template("Recipes.html")



   ######################## Other ########################
@app.route("/About")
def about():
	return render_template("About.html")


@app.route("/MyAccount")
def myAccount():
	return render_template("AccountInfo.html")



app.run(host="localhost", port=8000, debug=True)