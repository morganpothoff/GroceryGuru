
DROP TABLE IF EXISTS "Persons" CASCADE;
CREATE TABLE "Persons" (
	"id" SERIAL NOT NULL PRIMARY KEY,
	"email" VARCHAR(255) UNIQUE,
	"name" VARCHAR(255),
	"password" VARCHAR(255)  -- TODO: Don't store as plain text
);


DROP TABLE IF EXISTS "Ingredients" CASCADE;
CREATE TABLE "Ingredients" (
	"id" SERIAL NOT NULL PRIMARY KEY,
	"item_name" VARCHAR(255) NOT NULL,
	"brand_name" VARCHAR(255),	-- Null indicates brand does not matter
	"is_deleted" BOOLEAN NOT NULL DEFAULT FALSE,
	"Persons.id" INT NOT NULL,
	FOREIGN KEY ("Persons.id") REFERENCES "Persons"("id")
);


-- item_name, brand_name, Persons.id must be unique if not deleted.
CREATE UNIQUE INDEX "Ingredients__item_name__brand_name__Persons_id_WHERE_is_deleted"
  ON "Ingredients" ("item_name", "brand_name", "Persons.id")
  WHERE "is_deleted" = FALSE;


DROP TABLE IF EXISTS "HomeIngredients" CASCADE;
CREATE TABLE "HomeIngredients" (
	"id" SERIAL NOT NULL PRIMARY KEY,
	"count" DECIMAL NOT NULL,
	"date_purchased" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	"date_expires" TIMESTAMP,  -- Null indicates item does not expire
	"is_deleted" BOOLEAN NOT NULL DEFAULT FALSE,
	"Ingredients.id" INT NOT NULL,
	FOREIGN KEY ("Ingredients.id") REFERENCES "Ingredients"("id")
);


-- Deletes HomeIngredients when Ingredients is deleted
CREATE RULE "UpdateDeleteIngredient" AS ON UPDATE TO "Ingredients"
WHERE NEW."is_deleted" = TRUE
DO (
	UPDATE "HomeIngredients"
	SET "is_deleted" = TRUE
	WHERE "Ingredients.id" = NEW."id";
);
