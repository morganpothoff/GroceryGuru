
DROP TABLE IF EXISTS "Persons" CASCADE;
CREATE TABLE "Persons" (
	"id" SERIAL NOT NULL PRIMARY KEY,
	"email" VARCHAR(255) UNIQUE,
	"name" VARCHAR(255),
	"password" VARCHAR(255)  -- pbkdf2:sha256 hash
);


DROP TABLE IF EXISTS "Lists" CASCADE;
CREATE TABLE "Lists" (
	"id" SERIAL NOT NULL PRIMARY KEY,
	"name" VARCHAR(255) NOT NULL,
	"Persons.id" INT NOT NULL,
	FOREIGN KEY ("Persons.id") REFERENCES "Persons"("id")
);


DROP TABLE IF EXISTS "StorageTypes" CASCADE;
CREATE TABLE "StorageTypes" (
	"id" SERIAL NOT NULL PRIMARY KEY,
	"name" VARCHAR(255) NOT NULL,
	"Ingredients.id" INT NOT NULL,
	FOREIGN KEY ("Ingredients.id") REFERENCES "Ingredients"("id")
);


-- ——————————————————————————————— Ingredients —————————————————————————————— --

DROP TABLE IF EXISTS "Ingredients" CASCADE;
CREATE TABLE "Ingredients" (
	"id" SERIAL NOT NULL PRIMARY KEY,
	"name" VARCHAR(255) NOT NULL,
	"is_deleted" BOOLEAN NOT NULL DEFAULT FALSE,
	"Persons.id" INT NOT NULL,
	FOREIGN KEY ("Persons.id") REFERENCES "Persons"("id")
);


-- iname, brand_name, Persons.id must be unique if not deleted.
-- CREATE UNIQUE INDEX "Ingredients__item_name__brand_name__Persons_id_WHERE_is_deleted"
-- 	ON "Ingredients" ("name", "brand_name", "Persons.id")
-- 	WHERE "is_deleted" = FALSE;


DROP TABLE IF EXISTS "ListIngredients" CASCADE;
CREATE TABLE "ListIngredients" (
	"id" SERIAL NOT NULL PRIMARY KEY,
	"quantity" INT NOT NULL,
	"date_added" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	"is_deleted" BOOLEAN NOT NULL DEFAULT FALSE,
	"Ingredients.id" INT NOT NULL,
	"Lists.id" INT NOT NULL,
	FOREIGN KEY ("Ingredients.id") REFERENCES "Ingredients"("id"),
	FOREIGN KEY ("Lists.id") REFERENCES "Lists"("id")
);


DROP TABLE IF EXISTS "InventoryIngredients" CASCADE;
CREATE TABLE "InventoryIngredients" (
	"id" SERIAL NOT NULL PRIMARY KEY,
	"count" INT NOT NULL,
	"date_purchased" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	"date_expires" TIMESTAMP,  -- Null indicates item does not expire
	"Ingredients.id" INT NOT NULL,
	"ListIngredients.id" INT DEFAULT NULL,	-- Null indicated item is not from a list
	"is_deleted" BOOLEAN NOT NULL DEFAULT FALSE,
	FOREIGN KEY ("Ingredients.id") REFERENCES "Ingredients"("id"),
	FOREIGN KEY ("ListIngredients.id") REFERENCES "ListIngredients"("id")
);


-- Deletes HomeIngredients when Ingredients is deleted
CREATE RULE "UpdateDeleteIngredient" AS ON UPDATE TO "Ingredients"
WHERE NEW."is_deleted" = TRUE
DO (
	UPDATE "InventoryIngredients"
	SET "is_deleted" = TRUE
	WHERE "Ingredients.id" = NEW."id";
);
