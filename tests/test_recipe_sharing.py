"""Unit tests for the recipe sharing feature: share with friends, notifications, add to recipes."""
import json
import pytest

from database import (
	create_user,
	create_recipe,
	create_friend_request,
	accept_friend_request,
	create_recipe_share,
	share_recipe_with_friends,
	add_shared_recipe_to_user,
	dismiss_notification,
)
from database import Select


# ————————————————————————————————— Fixtures ————————————————————————————————— #

@pytest.fixture
def sharer_id():
	"""Create a user who will share a recipe."""
	email = f"sharer_{id(object())}@test.com"
	return create_user(email, "Recipe Sharer", "Pass123")


@pytest.fixture
def recipient_id():
	"""Create a user who will receive a shared recipe."""
	email = f"recipient_{id(object())}@test.com"
	return create_user(email, "Recipe Recipient", "Pass456")


@pytest.fixture
def second_recipient_id():
	"""Create a second recipient for multi-share tests."""
	email = f"recipient2_{id(object())}@test.com"
	return create_user(email, "Second Recipient", "Pass789")


@pytest.fixture
def shared_recipe(sharer_id):
	"""Create a recipe owned by sharer."""
	return create_recipe(
		title="Shared Chocolate Cake",
		Persons_id=sharer_id,
		ingredients="2 cups flour\n1 cup sugar\n3 eggs",
		steps="Mix ingredients\nBake at 350°F\nCool",
		special_notes="Serves 8",
		source_url="https://example.com/cake",
		category="Desserts",
	)


@pytest.fixture
def friends(sharer_id, recipient_id):
	"""Make sharer and recipient friends."""
	create_friend_request(sharer_id, recipient_id)
	req = Select.get_pending_friend_requests_for_user(recipient_id)[0][0]
	accept_friend_request(req.id, recipient_id)
	return (sharer_id, recipient_id)


@pytest.fixture
def recipe_share(sharer_id, recipient_id, shared_recipe, friends):
	"""Create a recipe share from sharer to recipient."""
	return create_recipe_share(shared_recipe, sharer_id, recipient_id)


# ————————————————————————————————— Database: create_recipe_share ———————————— #

class TestCreateRecipeShare:
	"""Tests for create_recipe_share database function."""

	def test_create_recipe_share_success(self, sharer_id, recipient_id, shared_recipe, friends):
		"""create_recipe_share creates a share and returns share id."""
		share_id = create_recipe_share(shared_recipe, sharer_id, recipient_id)
		assert share_id is not None

		shares = Select.get_recipe_shares_for_recipient(recipient_id)
		assert len(shares) == 1
		share, recipe, sharer = shares[0]
		assert share.id == share_id
		assert recipe.id == shared_recipe
		assert recipe.title == "Shared Chocolate Cake"
		assert sharer.id == sharer_id

	def test_create_recipe_share_self_raises(self, sharer_id, shared_recipe):
		"""create_recipe_share raises when sharer equals recipient."""
		with pytest.raises(ValueError, match="cannot share a recipe with yourself"):
			create_recipe_share(shared_recipe, sharer_id, sharer_id)

	def test_create_recipe_share_duplicate_raises(self, sharer_id, recipient_id, shared_recipe, friends):
		"""create_recipe_share raises when already shared with that friend."""
		create_recipe_share(shared_recipe, sharer_id, recipient_id)
		with pytest.raises(ValueError, match="already shared"):
			create_recipe_share(shared_recipe, sharer_id, recipient_id)

	def test_create_recipe_share_nonexistent_recipe_raises(self, sharer_id, recipient_id, friends):
		"""create_recipe_share raises when recipe does not exist or not owned by sharer."""
		with pytest.raises(ValueError, match="Recipe not found"):
			create_recipe_share(99999, sharer_id, recipient_id)


# ————————————————————————————————— Database: share_recipe_with_friends —————— #

class TestShareRecipeWithFriends:
	"""Tests for share_recipe_with_friends database function."""

	def test_share_with_multiple_friends(
		self, sharer_id, recipient_id, second_recipient_id, shared_recipe
	):
		"""share_recipe_with_friends creates shares for each recipient."""
		create_friend_request(sharer_id, recipient_id)
		req1 = Select.get_pending_friend_requests_for_user(recipient_id)[0][0]
		accept_friend_request(req1.id, recipient_id)

		create_friend_request(sharer_id, second_recipient_id)
		req2 = Select.get_pending_friend_requests_for_user(second_recipient_id)[0][0]
		accept_friend_request(req2.id, second_recipient_id)

		success_count, errors = share_recipe_with_friends(
			shared_recipe, sharer_id, [recipient_id, second_recipient_id]
		)
		assert success_count == 2
		assert len(errors) == 0

		shares1 = Select.get_recipe_shares_for_recipient(recipient_id)
		shares2 = Select.get_recipe_shares_for_recipient(second_recipient_id)
		assert len(shares1) == 1
		assert len(shares2) == 1

	def test_share_with_friends_skips_self(self, sharer_id, recipient_id, shared_recipe, friends):
		"""share_recipe_with_friends skips sharer in recipient list."""
		success_count, errors = share_recipe_with_friends(
			shared_recipe, sharer_id, [recipient_id, sharer_id]
		)
		assert success_count == 1
		shares = Select.get_recipe_shares_for_recipient(recipient_id)
		assert len(shares) == 1

	def test_share_with_friends_handles_duplicate(
		self, sharer_id, recipient_id, shared_recipe, friends
	):
		"""share_recipe_with_friends reports error for already-shared friend but succeeds for new."""
		create_recipe_share(shared_recipe, sharer_id, recipient_id)

		other_id = create_user(f"other_{id(object())}@test.com", "Other", "pass")
		create_friend_request(sharer_id, other_id)
		req = Select.get_pending_friend_requests_for_user(other_id)[0][0]
		accept_friend_request(req.id, other_id)

		success_count, errors = share_recipe_with_friends(
			shared_recipe, sharer_id, [recipient_id, other_id]
		)
		assert success_count == 1
		assert len(errors) >= 1
		assert "already shared" in errors[0].lower()


# ————————————————————————————————— Database: add_shared_recipe_to_user —————— #

class TestAddSharedRecipeToUser:
	"""Tests for add_shared_recipe_to_user database function."""

	def test_add_shared_recipe_success(self, recipe_share, recipient_id, shared_recipe):
		"""add_shared_recipe_to_user copies recipe to recipient and returns new recipe id."""
		new_id = add_shared_recipe_to_user(recipe_share, recipient_id)
		assert new_id is not None

		recipe = Select.get_Recipe_by_id(new_id, recipient_id)
		assert recipe is not None
		assert recipe.title == "Shared Chocolate Cake"
		assert "flour" in recipe.ingredients
		assert "Mix ingredients" in recipe.steps
		assert recipe.special_notes == "Serves 8"
		assert recipe.source_url == "https://example.com/cake"
		assert recipe.category == "Desserts"
		assert new_id != shared_recipe

	def test_add_shared_recipe_copies_images(
		self, sharer_id, recipient_id, shared_recipe, friends
	):
		"""add_shared_recipe_to_user copies recipe images to the new recipe."""
		from database import create_recipe_image
		create_recipe_image(shared_recipe, "uploads/recipes/cake.jpg")
		share_id = create_recipe_share(shared_recipe, sharer_id, recipient_id)

		new_id = add_shared_recipe_to_user(share_id, recipient_id)
		images = Select.get_recipe_images(new_id)
		assert len(images) == 1
		assert images[0].file_path == "uploads/recipes/cake.jpg"

	def test_add_shared_recipe_wrong_recipient_returns_none(
		self, recipe_share, recipient_id, sharer_id
	):
		"""add_shared_recipe_to_user returns None when recipient doesn't match."""
		other_id = create_user(f"other_{id(object())}@test.com", "Other", "pass")
		result = add_shared_recipe_to_user(recipe_share, other_id)
		assert result is None

		# Recipient's recipes unchanged
		recipes = Select.get_Recipes_by_Persons_id(recipient_id)
		titles = [r.title for r in recipes]
		assert "Shared Chocolate Cake" not in titles

	def test_add_shared_recipe_nonexistent_share_returns_none(self, recipient_id):
		"""add_shared_recipe_to_user returns None for invalid share id."""
		result = add_shared_recipe_to_user(99999, recipient_id)
		assert result is None


# ————————————————————————————————— Database: Select —————————————————————————— #

class TestRecipeShareSelect:
	"""Tests for recipe share Select functions."""

	def test_get_recipe_shares_for_recipient_empty(self, recipient_id):
		"""get_recipe_shares_for_recipient returns empty when no shares."""
		shares = Select.get_recipe_shares_for_recipient(recipient_id)
		assert shares == []

	def test_get_recipe_shares_for_recipient_returns_shares(
		self, recipe_share, recipient_id, shared_recipe, sharer_id
	):
		"""get_recipe_shares_for_recipient returns (share, recipe, sharer) tuples."""
		shares = Select.get_recipe_shares_for_recipient(recipient_id)
		assert len(shares) == 1
		share, recipe, sharer = shares[0]
		assert share.id == recipe_share
		assert recipe.id == shared_recipe
		assert sharer.id == sharer_id
		assert sharer.name == "Recipe Sharer"

	def test_get_recipe_share_by_id_success(self, recipe_share, recipient_id):
		"""get_recipe_share_by_id returns share when recipient matches."""
		row = Select.get_recipe_share_by_id(recipe_share, recipient_id)
		assert row is not None
		share, recipe, sharer = row
		assert share.id == recipe_share
		assert recipe.title == "Shared Chocolate Cake"

	def test_get_recipe_share_by_id_wrong_recipient_returns_none(
		self, recipe_share, recipient_id, sharer_id
	):
		"""get_recipe_share_by_id returns None when recipient doesn't match."""
		row = Select.get_recipe_share_by_id(recipe_share, sharer_id)
		assert row is None

	def test_get_recipe_share_by_id_nonexistent_returns_none(self, recipient_id):
		"""get_recipe_share_by_id returns None for invalid share id."""
		row = Select.get_recipe_share_by_id(99999, recipient_id)
		assert row is None

	def test_get_recipe_shares_excludes_dismissed(self, recipe_share, recipient_id):
		"""get_recipe_shares_for_recipient excludes dismissed shares."""
		shares = Select.get_recipe_shares_for_recipient(recipient_id)
		assert len(shares) == 1
		dismiss_notification(recipient_id, "recipe_share", recipe_share)
		shares_after = Select.get_recipe_shares_for_recipient(recipient_id)
		assert len(shares_after) == 0


# ————————————————————————————————— Database: dismiss_notification ——————————— #

class TestDismissNotification:
	"""Tests for dismiss_notification database function."""

	def test_dismiss_notification_recipe_share(self, recipe_share, recipient_id):
		"""dismiss_notification records recipe_share dismissal."""
		result = dismiss_notification(recipient_id, "recipe_share", recipe_share)
		assert result is True
		shares = Select.get_recipe_shares_for_recipient(recipient_id)
		assert len(shares) == 0

	def test_dismiss_notification_friend_request(self, sharer_id, recipient_id):
		"""dismiss_notification records friend_request dismissal."""
		create_friend_request(sharer_id, recipient_id)
		req = Select.get_pending_friend_requests_for_user(recipient_id)[0][0]
		result = dismiss_notification(recipient_id, "friend_request", req.id)
		assert result is True
		pending = Select.get_pending_friend_requests_for_user(recipient_id)
		assert len(pending) == 0

	def test_dismiss_notification_invalid_type_returns_false(self, recipe_share, recipient_id):
		"""dismiss_notification returns False for invalid notification_type."""
		result = dismiss_notification(recipient_id, "invalid_type", recipe_share)
		assert result is False
		shares = Select.get_recipe_shares_for_recipient(recipient_id)
		assert len(shares) == 1

	def test_dismiss_notification_idempotent(self, recipe_share, recipient_id):
		"""dismiss_notification is idempotent - calling twice still works."""
		dismiss_notification(recipient_id, "recipe_share", recipe_share)
		result = dismiss_notification(recipient_id, "recipe_share", recipe_share)
		assert result is True
		shares = Select.get_recipe_shares_for_recipient(recipient_id)
		assert len(shares) == 0


# ————————————————————————————————— Routes: share recipe ——————————————————— #

class TestShareRecipeRoute:
	"""Tests for POST /Recipe/<id>/share."""

	def test_share_recipe_requires_login(self, client, sharer_id, shared_recipe):
		"""POST /Recipe/<id>/share returns 401/302 when not authenticated."""
		resp = client.post(
			f"/Recipe/{shared_recipe}/share",
			data=json.dumps({"recipient_ids": [1]}),
			content_type="application/json",
			follow_redirects=False,
		)
		assert resp.status_code in (302, 401)

	def test_share_recipe_success(self, logged_in_client, sharer_id, recipient_id, shared_recipe, friends):
		"""POST /Recipe/<id>/share with valid friend ids returns success."""
		client, user_id = logged_in_client
		# logged_in_client uses different user - we need sharer to be logged in
		# So we need: sharer = logged in user, recipient = friend
		# Create setup: user_id (logged in) = sharer, recipient_id = friend
		create_friend_request(user_id, recipient_id)
		req = Select.get_pending_friend_requests_for_user(recipient_id)[0][0]
		accept_friend_request(req.id, recipient_id)

		rid = create_recipe("To Share", user_id, ingredients="flour")
		resp = client.post(
			f"/Recipe/{rid}/share",
			data=json.dumps({"recipient_ids": [recipient_id]}),
			content_type="application/json",
			follow_redirects=False,
		)
		assert resp.status_code == 200
		data = resp.get_json()
		assert data["success"] is True
		assert data["shared_count"] == 1

		shares = Select.get_recipe_shares_for_recipient(recipient_id)
		assert len(shares) == 1
		assert shares[0][1].title == "To Share"

	def test_share_recipe_empty_recipients_returns_400(self, logged_in_client):
		"""POST /Recipe/<id>/share with no recipients returns 400."""
		client, user_id = logged_in_client
		rid = create_recipe("Empty Share Test", user_id)
		resp = client.post(
			f"/Recipe/{rid}/share",
			data=json.dumps({"recipient_ids": []}),
			content_type="application/json",
			follow_redirects=False,
		)
		assert resp.status_code == 400
		data = resp.get_json()
		assert data["success"] is False

	def test_share_recipe_404_for_nonexistent(self, logged_in_client):
		"""POST /Recipe/99999/share returns 404."""
		client, _ = logged_in_client
		resp = client.post(
			"/Recipe/99999/share",
			data=json.dumps({"recipient_ids": [1]}),
			content_type="application/json",
			follow_redirects=False,
		)
		assert resp.status_code == 404

	def test_share_recipe_404_for_other_user_recipe(
		self, logged_in_client, sharer_id, shared_recipe, recipient_id, friends
	):
		"""POST /Recipe/<id>/share returns 404 when recipe belongs to another user."""
		client, _ = logged_in_client
		# shared_recipe belongs to sharer_id, logged_in_client is different user
		resp = client.post(
			f"/Recipe/{shared_recipe}/share",
			data=json.dumps({"recipient_ids": [recipient_id]}),
			content_type="application/json",
			follow_redirects=False,
		)
		assert resp.status_code == 404


# ————————————————————————————————— Routes: shared recipe detail ———————————— #

class TestSharedRecipeDetailRoute:
	"""Tests for GET and POST /Recipe/Shared/<share_id>."""

	def test_shared_recipe_requires_login(self, client, recipe_share):
		"""GET /Recipe/Shared/<id> redirects when not authenticated."""
		resp = client.get(f"/Recipe/Shared/{recipe_share}", follow_redirects=False)
		assert resp.status_code in (302, 401)

	def test_shared_recipe_get_success(self, logged_in_client, recipe_share, recipient_id):
		"""GET /Recipe/Shared/<id> shows recipe when recipient is logged in."""
		client, user_id = logged_in_client
		# We need recipient to be the logged-in user
		# logged_in_client creates its own user. We need to log in as recipient.
		# Create recipient and log in as them
		email = f"shared_recipient_{id(object())}@test.com"
		rec_id = create_user(email, "Shared Recipient", "Pass123")
		client.post("/Logout", follow_redirects=True)
		client.post("/Login", data={"email": email, "pass": "Pass123"}, follow_redirects=True)

		# Create share to this recipient
		sharer_id = create_user(f"shared_sharer_{id(object())}@test.com", "Sharer", "pass")
		create_friend_request(sharer_id, rec_id)
		req = Select.get_pending_friend_requests_for_user(rec_id)[0][0]
		accept_friend_request(req.id, rec_id)
		rid = create_recipe("Shared View Test", sharer_id, ingredients="eggs")
		share_id = create_recipe_share(rid, sharer_id, rec_id)

		resp = client.get(f"/Recipe/Shared/{share_id}", follow_redirects=True)
		assert resp.status_code == 200
		assert b"Shared View Test" in resp.data
		assert b"eggs" in resp.data
		assert b"Add to my recipes" in resp.data
		assert b"Exit without adding" in resp.data
		assert b"Shared by" in resp.data
		assert b"Sharer" in resp.data

	def test_shared_recipe_viewing_auto_dismisses_notification(self, logged_in_client, recipe_share, recipient_id):
		"""GET /Recipe/Shared/<id> auto-dismisses the notification so it no longer appears."""
		email = f"auto_dismiss_{id(object())}@test.com"
		rec_id = create_user(email, "Auto Dismiss Recipient", "Pass123")
		client, _ = logged_in_client
		client.post("/Logout", follow_redirects=True)
		client.post("/Login", data={"email": email, "pass": "Pass123"}, follow_redirects=True)

		sharer_id = create_user(f"auto_dismiss_sharer_{id(object())}@test.com", "Sharer", "pass")
		create_friend_request(sharer_id, rec_id)
		req = Select.get_pending_friend_requests_for_user(rec_id)[0][0]
		accept_friend_request(req.id, rec_id)
		rid = create_recipe("Auto Dismiss Recipe", sharer_id)
		share_id = create_recipe_share(rid, sharer_id, rec_id)

		shares_before = Select.get_recipe_shares_for_recipient(rec_id)
		assert len(shares_before) == 1

		client.get(f"/Recipe/Shared/{share_id}", follow_redirects=True)

		shares_after = Select.get_recipe_shares_for_recipient(rec_id)
		assert len(shares_after) == 0

	def test_shared_recipe_post_add(self, logged_in_client, recipe_share, recipient_id, shared_recipe):
		"""POST /Recipe/Shared/<id> with action=add copies recipe to user."""
		email = f"add_recipient_{id(object())}@test.com"
		rec_id = create_user(email, "Add Recipient", "Pass123")
		client, _ = logged_in_client
		client.post("/Logout", follow_redirects=True)
		client.post("/Login", data={"email": email, "pass": "Pass123"}, follow_redirects=True)

		sharer_id = create_user(f"add_sharer_{id(object())}@test.com", "Sharer", "pass")
		create_friend_request(sharer_id, rec_id)
		req = Select.get_pending_friend_requests_for_user(rec_id)[0][0]
		accept_friend_request(req.id, rec_id)
		rid = create_recipe("To Add Recipe", sharer_id, ingredients="flour\nsugar")
		share_id = create_recipe_share(rid, sharer_id, rec_id)

		resp = client.post(
			f"/Recipe/Shared/{share_id}",
			data={"action": "add"},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=True,
		)
		assert resp.status_code == 200

		recipes = Select.get_Recipes_by_Persons_id(rec_id)
		titles = [r.title for r in recipes]
		assert "To Add Recipe" in titles

	def test_shared_recipe_404_for_wrong_recipient(
		self, logged_in_client, recipe_share, recipient_id, sharer_id
	):
		"""GET /Recipe/Shared/<id> returns 404 when current user is not the recipient."""
		client, _ = logged_in_client
		# logged_in_client is different from recipient_id
		resp = client.get(f"/Recipe/Shared/{recipe_share}", follow_redirects=False)
		assert resp.status_code == 404

	def test_shared_recipe_404_for_nonexistent(self, logged_in_client):
		"""GET /Recipe/Shared/99999 returns 404."""
		client, _ = logged_in_client
		resp = client.get("/Recipe/Shared/99999", follow_redirects=False)
		assert resp.status_code == 404


# ————————————————————————————————— Routes: dismiss notification ———————————— #

class TestDismissNotificationRoute:
	"""Tests for POST /Notifications/Dismiss."""

	def test_dismiss_route_requires_login(self, client, recipe_share):
		"""POST /Notifications/Dismiss redirects when not authenticated."""
		resp = client.post(
			"/Notifications/Dismiss",
			data={"notification_type": "recipe_share", "notification_id": recipe_share},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=False,
		)
		assert resp.status_code in (302, 401)

	def test_dismiss_route_recipe_share(self, logged_in_client, recipe_share, recipient_id):
		"""POST /Notifications/Dismiss with recipe_share dismisses and redirects."""
		email = f"dismiss_route_{id(object())}@test.com"
		rec_id = create_user(email, "Dismiss Recipient", "Pass123")
		client, _ = logged_in_client
		client.post("/Logout", follow_redirects=True)
		client.post("/Login", data={"email": email, "pass": "Pass123"}, follow_redirects=True)

		sharer_id = create_user(f"dismiss_sharer_{id(object())}@test.com", "Sharer", "pass")
		create_friend_request(sharer_id, rec_id)
		req = Select.get_pending_friend_requests_for_user(rec_id)[0][0]
		accept_friend_request(req.id, rec_id)
		rid = create_recipe("Dismiss Route Recipe", sharer_id)
		share_id = create_recipe_share(rid, sharer_id, rec_id)

		shares_before = Select.get_recipe_shares_for_recipient(rec_id)
		assert len(shares_before) == 1

		resp = client.post(
			"/Notifications/Dismiss",
			data={"notification_type": "recipe_share", "notification_id": share_id},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=True,
		)
		assert resp.status_code == 200
		shares_after = Select.get_recipe_shares_for_recipient(rec_id)
		assert len(shares_after) == 0

	def test_dismiss_route_friend_request(self, logged_in_client, sharer_id, recipient_id):
		"""POST /Notifications/Dismiss with friend_request dismisses and redirects."""
		create_friend_request(sharer_id, recipient_id)
		req = Select.get_pending_friend_requests_for_user(recipient_id)[0][0]

		email = f"dismiss_fr_{id(object())}@test.com"
		rec_id = create_user(email, "Dismiss FR Recipient", "Pass123")
		client, _ = logged_in_client
		client.post("/Logout", follow_redirects=True)
		client.post("/Login", data={"email": email, "pass": "Pass123"}, follow_redirects=True)

		requester_id = create_user(f"dismiss_requester_{id(object())}@test.com", "Requester", "pass")
		create_friend_request(requester_id, rec_id)
		req_id = Select.get_pending_friend_requests_for_user(rec_id)[0][0].id

		pending_before = Select.get_pending_friend_requests_for_user(rec_id)
		assert len(pending_before) == 1

		resp = client.post(
			"/Notifications/Dismiss",
			data={"notification_type": "friend_request", "notification_id": req_id},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=True,
		)
		assert resp.status_code == 200
		pending_after = Select.get_pending_friend_requests_for_user(rec_id)
		assert len(pending_after) == 0

	def test_dismiss_route_redirects_to_notifications(self, logged_in_client, recipe_share, recipient_id):
		"""POST /Notifications/Dismiss redirects to notifications page."""
		email = f"dismiss_redirect_{id(object())}@test.com"
		rec_id = create_user(email, "Redirect Recipient", "Pass123")
		client, _ = logged_in_client
		client.post("/Logout", follow_redirects=True)
		client.post("/Login", data={"email": email, "pass": "Pass123"}, follow_redirects=True)

		sharer_id = create_user(f"dismiss_redirect_sharer_{id(object())}@test.com", "Sharer", "pass")
		create_friend_request(sharer_id, rec_id)
		req = Select.get_pending_friend_requests_for_user(rec_id)[0][0]
		accept_friend_request(req.id, rec_id)
		rid = create_recipe("Redirect Recipe", sharer_id)
		share_id = create_recipe_share(rid, sharer_id, rec_id)

		resp = client.post(
			"/Notifications/Dismiss",
			data={"notification_type": "recipe_share", "notification_id": share_id},
			content_type="application/x-www-form-urlencoded",
			follow_redirects=False,
		)
		assert resp.status_code == 302
		assert "Notifications" in resp.headers.get("Location", "")


# ————————————————————————————————— Routes: notifications ——————————————————— #

class TestNotificationsRecipeShares:
	"""Tests that notifications page includes recipe shares."""

	def test_dismiss_recipe_share_hides_from_notifications(self, recipe_share, recipient_id):
		"""dismiss_notification hides recipe share from get_recipe_shares_for_recipient."""
		shares_before = Select.get_recipe_shares_for_recipient(recipient_id)
		assert len(shares_before) == 1

		dismiss_notification(recipient_id, "recipe_share", recipe_share)
		shares_after = Select.get_recipe_shares_for_recipient(recipient_id)
		assert len(shares_after) == 0

	def test_dismiss_friend_request_hides_from_pending(self, sharer_id, recipient_id, shared_recipe):
		"""dismiss_notification hides friend request from get_pending_friend_requests_for_user."""
		create_friend_request(sharer_id, recipient_id)
		pending_before = Select.get_pending_friend_requests_for_user(recipient_id)
		assert len(pending_before) == 1
		req_id = pending_before[0][0].id

		dismiss_notification(recipient_id, "friend_request", req_id)
		pending_after = Select.get_pending_friend_requests_for_user(recipient_id)
		assert len(pending_after) == 0

	def test_notifications_shows_recipe_shares(self, logged_in_client, recipe_share, recipient_id):
		"""GET /Friends/Notifications shows shared recipes when recipient is logged in."""
		email = f"notif_recipient_{id(object())}@test.com"
		rec_id = create_user(email, "Notif Recipient", "Pass123")
		client, _ = logged_in_client
		client.post("/Logout", follow_redirects=True)
		client.post("/Login", data={"email": email, "pass": "Pass123"}, follow_redirects=True)

		sharer_id = create_user(f"notif_sharer_{id(object())}@test.com", "Notif Sharer", "pass")
		create_friend_request(sharer_id, rec_id)
		req = Select.get_pending_friend_requests_for_user(rec_id)[0][0]
		accept_friend_request(req.id, rec_id)
		rid = create_recipe("Notif Shared Recipe", sharer_id)
		create_recipe_share(rid, sharer_id, rec_id)

		resp = client.get("/Friends/Notifications", follow_redirects=True)
		assert resp.status_code == 200
		assert b"Shared recipes" in resp.data
		assert b"Notif Shared Recipe" in resp.data
		assert b"View recipe" in resp.data
		assert b"notification-dismiss" in resp.data or b"aria-label=\"Dismiss\"" in resp.data

	def test_notifications_shows_dismiss_button_for_friend_requests(self, logged_in_client, sharer_id, recipient_id):
		"""GET /Friends/Notifications shows dismiss button for friend requests."""
		create_friend_request(sharer_id, recipient_id)
		email = f"dismiss_btn_{id(object())}@test.com"
		rec_id = create_user(email, "Dismiss Btn Recipient", "Pass123")
		client, _ = logged_in_client
		client.post("/Logout", follow_redirects=True)
		client.post("/Login", data={"email": email, "pass": "Pass123"}, follow_redirects=True)
		requester_id = create_user(f"dismiss_btn_req_{id(object())}@test.com", "Requester", "pass")
		create_friend_request(requester_id, rec_id)

		resp = client.get("/Friends/Notifications", follow_redirects=True)
		assert resp.status_code == 200
		assert b"Friend requests" in resp.data
		assert b"aria-label=\"Dismiss\"" in resp.data
