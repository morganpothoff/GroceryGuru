"""Unit tests for Privacy, Terms, and Contact pages."""
import pytest


class TestLegalPages:
	"""Tests for /Privacy, /Terms, and /Contact routes."""

	def test_privacy_returns_200(self, client):
		"""GET /Privacy returns 200 and real content (not placeholder)."""
		resp = client.get("/Privacy", follow_redirects=True)
		assert resp.status_code == 200
		assert b"Privacy Policy" in resp.data
		assert b"Information We Collect" in resp.data
		assert b"This page is coming soon" not in resp.data

	def test_terms_returns_200(self, client):
		"""GET /Terms returns 200 and real content (not placeholder)."""
		resp = client.get("/Terms", follow_redirects=True)
		assert resp.status_code == 200
		assert b"Terms of Service" in resp.data
		assert b"Acceptance of Terms" in resp.data
		assert b"This page is coming soon" not in resp.data

	def test_contact_returns_200(self, client):
		"""GET /Contact returns 200 and real content (not placeholder)."""
		resp = client.get("/Contact", follow_redirects=True)
		assert resp.status_code == 200
		assert b"Contact" in resp.data
		assert b"Get in Touch" in resp.data or b"support" in resp.data.lower()
		assert b"This page is coming soon" not in resp.data
