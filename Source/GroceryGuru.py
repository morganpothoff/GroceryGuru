#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from flask import *
from datetime import datetime
import database.DatabaseConnection
import json
import os

#import DB_Connections


app = Flask(__name__, static_url_path="/static")


@app.route("/")
def openingHome():
	return render_template("OpeningHome.html")

# @app.route("/")
# def home():
# 	return render_template("Home.html")

@app.route("/Login")
def login():
	return render_template("Login.html")


@app.route("/CreateAccount")
def createAccount():
	return render_template("CreateAccount.html")


@app.route("/MyPantry")
def myPantry():
	return render_template("MyPantry.html")


@app.route("/Recipes")
def recipes():
	return render_template("Recipes.html")


@app.route("/About")
def about():
	return render_template("About.html")


@app.route("/LearnMore")
def learnMore():
	return render_template("LearnMore.html")


@app.route("/MyAccount")
def myAccount():
	return render_template("AccountInfo.html")


app.run(host="localhost", port=8000, debug=True)