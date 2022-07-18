DROP TABLE IF EXISTS "Persons" CASCADE;
CREATE TABLE "Persons" (
	"PersonID" SERIAL NOT NULL PRIMARY KEY,
	"Email" VARCHAR(255) NOT NULL UNIQUE,
	"Username" VARCHAR(255) NOT NULL UNIQUE,
	"Password" VARCHAR(255) NOT NULL
);


INSERT INTO "Persons" ("Email", "Username", "Password") VALUES
	('morgan@groceryguru.com', 'morgan', 'morgan');


DROP TABLE IF EXISTS "Food" CASCADE;
CREATE TABLE "Food" (
	"FoodID" SERIAL NOT NULL PRIMARY KEY
);


DROP TABLE IF EXISTS "DefaultList" CASCADE;
CREATE TABLE "DefaultList" (
	"DefaultListID" SERIAL NOT NULL PRIMARY KEY,
	"Name" VARCHAR(255) NOT NULL UNIQUE
);


INSERT INTO "DefaultList" ("Name") VALUES
	('Grocery List'),
	('My Pantry'),
	('My Spices'),
	('My Fridge'),
	('My Tools');



DROP TABLE IF EXISTS "List" CASCADE;
CREATE TABLE "List" (
	"ListID" SERIAL NOT NULL PRIMARY KEY,
	"Name" VARCHAR(255) NOT NULL UNIQUE,
	"PersonID" INT NOT NULL,
	FOREIGN KEY("PersonID") REFERENCES "Persons"("PersonID"),
	UNIQUE("Name", "PersonID")
);


-- INSERT INTO "List" ("Name", "PersonID") VALUES
-- 	('Grocery List', 1);
INSERT INTO "List" ("Name", "PersonID")
SELECT "DefaultList"."Name", "Persons"."PersonID"
FROM "DefaultList"
JOIN "Persons" ON "Persons"."Username" = 'morgan';


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


