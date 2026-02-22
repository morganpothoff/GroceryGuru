#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract recipe data from URLs. Uses Schema.org Recipe JSON-LD when available,
with fallback heuristics. Returns only ingredients, steps, and special notes.
Category is inferred from website content when possible.
"""

import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Standard categories (empty string = Others)
RECIPE_CATEGORIES = ["Desserts", "Dinners", "Breakfasts"]
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def _normalize_category(raw: str) -> str:
	"""Map website category text to our standard categories, or '' for Others."""
	if not raw or not isinstance(raw, str):
		return ""
	lower = raw.lower().strip()
	# Desserts
	if any(k in lower for k in ["dessert", "desserts", "cake", "cakes", "cookie", "cookies", "pie", "pies", "brownie", "pastry"]):
		return "Desserts"
	# Dinners
	if any(k in lower for k in ["dinner", "dinners", "main", "mains", "entrée", "entree", "entrées", "entrees", "lunch", "supper"]):
		return "Dinners"
	# Breakfasts
	if any(k in lower for k in ["breakfast", "breakfasts", "brunch", "pancake", "waffle", "omelet", "omelette"]):
		return "Breakfasts"
	return ""


def _infer_category_from_text(text: str) -> str:
	"""Infer category from title or description text."""
	if not text:
		return ""
	return _normalize_category(text)


def _extract_instructions_from_schema(obj) -> str:
	"""Convert recipeInstructions to plain text steps."""
	instructions = obj.get("recipeInstructions") or obj.get("instructions")
	if not instructions:
		return ""
	if isinstance(instructions, str):
		return instructions.strip()
	if isinstance(instructions, list):
		steps = []
		for step in instructions:
			if isinstance(step, str):
				steps.append(step.strip())
			elif isinstance(step, dict):
				stext = step.get("text") or step.get("name") or step.get("@value") or ""
				if stext:
					steps.append(str(stext).strip())
			elif isinstance(step, (int, float)):
				steps.append(str(step))
		return "\n".join(s for s in steps if s)
	return str(instructions)


def _extract_image_from_schema(obj) -> str:
	"""Get recipe image URL from Schema.org. Returns first URL if image is a list."""
	img = obj.get("image")
	if not img:
		return ""
	if isinstance(img, str):
		return img.strip()
	if isinstance(img, list) and img:
		first = img[0]
		if isinstance(first, str):
			return first.strip()
		if isinstance(first, dict):
			url = first.get("url") or first.get("@id") or ""
			return str(url).strip() if url else ""
	return ""


def _extract_ingredients_from_schema(obj) -> str:
	"""Get ingredients as newline-separated text."""
	ingredients = obj.get("recipeIngredient")
	if not ingredients:
		return ""
	if isinstance(ingredients, str):
		return ingredients.strip()
	if isinstance(ingredients, list):
		return "\n".join(str(i).strip() for i in ingredients if i)
	return str(ingredients)


def _find_recipe_schema(soup: BeautifulSoup) -> dict | None:
	"""Find Schema.org Recipe in JSON-LD scripts."""
	for script in soup.find_all("script", type="application/ld+json"):
		try:
			data = json.loads(script.string or "{}")
		except json.JSONDecodeError:
			continue
		if not data:
			continue
		# Handle @graph
		items = data.get("@graph", [data]) if isinstance(data, dict) else [data]
		for item in items:
			if not isinstance(item, dict):
				continue
			typ = item.get("@type")
			if typ == "Recipe":
				return item
			if isinstance(typ, list) and "Recipe" in typ:
				return item
	return None


def extract_recipe_from_url(url: str) -> dict | None:
	"""
	Fetch a URL and extract recipe data. Returns dict with:
	  - title: str
	  - ingredients: str (newline-separated)
	  - steps: str (newline-separated)
	  - special_notes: str
	  - category: str (Desserts, Dinners, Breakfasts, or '' for Others)
	  - source_url: str

	Returns None on fetch/parse failure. Only returns core recipe content,
	no comments or user-generated content.
	"""
	try:
		resp = requests.get(url, timeout=15, headers={"User-Agent": USER_AGENT})
		resp.raise_for_status()
		text = resp.text
	except Exception:
		return None

	soup = BeautifulSoup(text, "html.parser")

	# Prefer Schema.org Recipe
	recipe_obj = _find_recipe_schema(soup)
	if recipe_obj:
		title = recipe_obj.get("name") or recipe_obj.get("headline") or "Untitled Recipe"
		if isinstance(title, list):
			title = title[0] if title else "Untitled Recipe"
		ingredients = _extract_ingredients_from_schema(recipe_obj)
		steps = _extract_instructions_from_schema(recipe_obj)
		notes_parts = []
		if recipe_obj.get("cookTime"):
			notes_parts.append(f"Cook time: {recipe_obj['cookTime']}")
		if recipe_obj.get("prepTime"):
			notes_parts.append(f"Prep time: {recipe_obj['prepTime']}")
		if recipe_obj.get("totalTime"):
			notes_parts.append(f"Total time: {recipe_obj['totalTime']}")
		if recipe_obj.get("recipeYield"):
			notes_parts.append(f"Yield: {recipe_obj['recipeYield']}")
		special_notes = "\n".join(notes_parts) if notes_parts else ""
		# Category from recipeCategory
		raw_cat = recipe_obj.get("recipeCategory")
		if isinstance(raw_cat, list) and raw_cat:
			raw_cat = raw_cat[0]
		category = _normalize_category(str(raw_cat) if raw_cat else "")
		if not category:
			category = _infer_category_from_text(title)
		image_url = _extract_image_from_schema(recipe_obj)
		return {
			"title": str(title).strip(),
			"ingredients": ingredients,
			"steps": steps,
			"special_notes": special_notes.strip(),
			"category": category,
			"source_url": url,
			"image_url": image_url,
		}

	# Fallback: look for common patterns (class names used by recipe sites)
	title_el = soup.find("h1") or soup.find(class_=re.compile(r"recipe-title|recipe-name|entry-title", re.I))
	title = (title_el.get_text(strip=True) if title_el else "") or "Untitled Recipe"

	ing_els = soup.find_all(class_=re.compile(r"ingredient|recipe-ingredient", re.I))
	ingredients = ""
	if ing_els:
		ingredients = "\n".join(el.get_text(strip=True) for el in ing_els if el.get_text(strip=True))
	else:
		for li in soup.find_all("li", class_=lambda c: c and "ingredient" in str(c).lower()):
			ingredients += li.get_text(strip=True) + "\n"
		ingredients = ingredients.strip()

	inst_els = soup.find_all(class_=re.compile(r"instruction|recipe-step|direction|recipe-direction", re.I))
	steps = ""
	if inst_els:
		steps = "\n".join(el.get_text(strip=True) for el in inst_els if el.get_text(strip=True))
	else:
		for li in soup.find_all("li", class_=lambda c: c and ("step" in str(c).lower() or "instruction" in str(c).lower())):
			steps += li.get_text(strip=True) + "\n"
		steps = steps.strip()

	category = _infer_category_from_text(title)
	return {
		"title": title,
		"ingredients": ingredients,
		"steps": steps,
		"special_notes": "",
		"category": category,
		"source_url": url,
		"image_url": "",
	}
