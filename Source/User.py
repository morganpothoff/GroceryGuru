#!/usr/bin/env python3
# -*- coding: utf-8 -*-


class User(object):
	def __init__(self, id_num, email, username, password):
		self.id = id_num
		self.email = email
		self.username = username
		self.password = password

	def is_authenticated(self):
		return True

	def is_active(self):
		return True

	def get_id(self):
		return str(self.id)
