-- SQLite schema for GroceryGuru

DROP TABLE IF EXISTS "InventoryIngredients";
DROP TABLE IF EXISTS "ListIngredients";
DROP TABLE IF EXISTS "Ingredients";
DROP TABLE IF EXISTS "StorageTypes";
DROP TABLE IF EXISTS "Lists";
DROP TABLE IF EXISTS "Persons";

CREATE TABLE "Persons" (
	"id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"email" TEXT UNIQUE,
	"name" TEXT,
	"password" TEXT  -- pbkdf2:sha256 hash
);

CREATE TABLE "Lists" (
	"id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"name" TEXT NOT NULL,
	"Persons.id" INTEGER NOT NULL,
	FOREIGN KEY ("Persons.id") REFERENCES "Persons"("id")
);

CREATE TABLE "Ingredients" (
	"id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"name" TEXT NOT NULL,
	"is_deleted" INTEGER NOT NULL DEFAULT 0,
	"Persons.id" INTEGER NOT NULL,
	FOREIGN KEY ("Persons.id") REFERENCES "Persons"("id")
);

CREATE TABLE "StorageTypes" (
	"id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"name" TEXT NOT NULL,
	"Ingredients.id" INTEGER NOT NULL,
	FOREIGN KEY ("Ingredients.id") REFERENCES "Ingredients"("id")
);

CREATE TABLE "ListIngredients" (
	"id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"quantity" INTEGER NOT NULL,
	"date_added" TEXT NOT NULL DEFAULT (datetime('now')),
	"is_deleted" INTEGER NOT NULL DEFAULT 0,
	"Ingredients.id" INTEGER NOT NULL,
	"Lists.id" INTEGER NOT NULL,
	FOREIGN KEY ("Ingredients.id") REFERENCES "Ingredients"("id"),
	FOREIGN KEY ("Lists.id") REFERENCES "Lists"("id")
);

CREATE TABLE "InventoryIngredients" (
	"id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"count" INTEGER NOT NULL,
	"date_purchased" TEXT NOT NULL DEFAULT (datetime('now')),
	"date_expires" TEXT,
	"notes" TEXT,
	"Ingredients.id" INTEGER NOT NULL,
	"ListIngredients.id" INTEGER DEFAULT NULL,
	"is_deleted" INTEGER NOT NULL DEFAULT 0,
	FOREIGN KEY ("Ingredients.id") REFERENCES "Ingredients"("id"),
	FOREIGN KEY ("ListIngredients.id") REFERENCES "ListIngredients"("id")
);

-- Trigger: soft-delete InventoryIngredients when Ingredients is soft-deleted
CREATE TRIGGER "UpdateDeleteIngredient" AFTER UPDATE ON "Ingredients"
WHEN NEW."is_deleted" = 1
BEGIN
	UPDATE "InventoryIngredients" SET "is_deleted" = 1 WHERE "Ingredients.id" = NEW."id";
END;

-- Recipes: ingredients, steps, notes, source URL, category (Desserts, Dinners, Breakfasts, or empty for Others)
CREATE TABLE IF NOT EXISTS "Recipes" (
	"id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"title" TEXT NOT NULL,
	"ingredients" TEXT NOT NULL DEFAULT '',
	"steps" TEXT NOT NULL DEFAULT '',
	"special_notes" TEXT DEFAULT '',
	"source_url" TEXT,
	"category" TEXT DEFAULT '',
	"Persons.id" INTEGER NOT NULL,
	"is_deleted" INTEGER NOT NULL DEFAULT 0,
	"date_added" TEXT NOT NULL DEFAULT (datetime('now')),
	FOREIGN KEY ("Persons.id") REFERENCES "Persons"("id")
);
