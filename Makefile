


clone:
	git clone git@github.com:morganpothoff/GroceryGuru.git


database:
	cd GroceryGuru/Database
	brew install postgres
	brew services restart postgresql@14
	createdb GroceryGuru
	psql GroceryGuru -f GroceryGuru.sql


python:
	pip3 install flask flask-login psycopg2


run:
	cd Source
	# Credentials
	python3 GroceryGuru.py