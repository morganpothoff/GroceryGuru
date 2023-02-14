

-- ------------------------------------------------------- Tables ------------------------------------------------------

DROP TABLE IF EXISTS "Persons" CASCADE;
CREATE TABLE "Persons" (
	"PersonID" SERIAL NOT NULL PRIMARY KEY,
	"Email" VARCHAR(255) NOT NULL UNIQUE,
	"Username" VARCHAR(255) NOT NULL UNIQUE,
	"Password" VARCHAR(255) NOT NULL
);


DROP TABLE IF EXISTS "Food" CASCADE;
CREATE TABLE "Food" (
	"FoodID" SERIAL NOT NULL PRIMARY KEY
);


DROP TABLE IF EXISTS "DefaultList" CASCADE;
CREATE TABLE "DefaultList" (
	"DefaultListID" SERIAL NOT NULL PRIMARY KEY,
	"Name" VARCHAR(255) NOT NULL UNIQUE
);


DROP TABLE IF EXISTS "List" CASCADE;
CREATE TABLE "List" (
	"ListID" SERIAL NOT NULL PRIMARY KEY,
	"Name" VARCHAR(255) NOT NULL,
	"PersonID" INT NOT NULL,
	FOREIGN KEY("PersonID") REFERENCES "Persons"("PersonID"),
	UNIQUE("Name", "PersonID")
);


DROP TABLE IF EXISTS "GroceryItem" CASCADE;
CREATE TABLE "GroceryItem" (
	"GroceryItemID" SERIAL NOT NULL PRIMARY KEY,
	"ListID" INT NOT NULL,
	"Name" VARCHAR(255) NOT NULL UNIQUE,
	"Quantity" INT NOT NULL,
	"PurchaseDate" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	"ExpirationDate" TIMESTAMP DEFAULT NULL,
	"OpeningDate" TIMESTAMP DEFAULT NULL,
	CONSTRAINT "Quantity" CHECK ("Quantity" > 0)
);



-- ------------------------------------------------------ Triggers -----------------------------------------------------

-- Adds default lists to each newly created user
CREATE OR REPLACE FUNCTION add_default_lists() RETURNS TRIGGER AS $$
	BEGIN
		INSERT INTO "List" ("Name", "PersonID")
		SELECT "DefaultList"."Name", NEW."PersonID"
		FROM "DefaultList";
		return NEW;
	END;
$$
language plpgsql volatile;

CREATE TRIGGER add_default_lists
	AFTER INSERT ON "Persons" FOR EACH ROW EXECUTE PROCEDURE add_default_lists();


-- Adds new default list to existing users
CREATE OR REPLACE FUNCTION update_existing_default_lists() RETURNS TRIGGER AS $$
	BEGIN
		INSERT INTO "List" ("Name", "PersonID")
		SELECT NEW."Name", "Persons"."PersonID"
		FROM "Persons";
		return NEW;
	END;
$$
language plpgsql volatile;

CREATE TRIGGER update_existing_default_lists
	AFTER INSERT ON "DefaultList" FOR EACH ROW EXECUTE PROCEDURE update_existing_default_lists();



-- ----------------------------------------------------- Insertions ----------------------------------------------------

INSERT INTO "DefaultList" ("Name") VALUES
	('Grocery List'),
	('My Pantry'),
	('My Spices'),
	('My Fridge'),
	('My Tools');


INSERT INTO "Persons" ("Email", "Username", "Password") VALUES
	('tester@groceryguru.com', 'tester', 'tester');



