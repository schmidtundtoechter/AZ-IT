# Copyright (c) 2025, ahmad mohammad and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class WANummer(Document):
	def before_insert(self):
		"""Generate WA Nummer automatically before inserting if not already set"""
		if not self.wa_nummer:
			self.wa_nummer = self.generate_wa_nummer()

		# Set contract conclusion date to today if not set
		if not self.vertragsabschluss:
			self.vertragsabschluss = frappe.utils.today()

		# Keep price fields as blank (None) if not explicitly provided
		if not self.aktueller_preis:
			self.aktueller_preis = None
		if not self.alter_preis:
			self.alter_preis = None

	def generate_wa_nummer(self):
		"""
		Generate a unique WA Nummer in the format WAXXXXX
		where XXXXX is a 5-digit sequential number
		"""
		# Find the highest existing WA Nummer
		existing_numbers = frappe.db.sql("""
			SELECT wa_nummer
			FROM `tabWA Nummer`
			WHERE wa_nummer LIKE 'WA%'
			ORDER BY wa_nummer DESC
			LIMIT 1
		""", as_dict=True)

		if existing_numbers:
			# Extract the numeric part from the last WA Nummer
			last_number = existing_numbers[0].get('wa_nummer', 'WA00000')
			try:
				# Remove 'WA' prefix and convert to integer
				numeric_part = int(last_number.replace('WA', ''))
				# Never generate below 1200 for new auto-numbers
				new_number = max(numeric_part + 1, 1200)
			except (ValueError, AttributeError):
				# If parsing fails, start from 1200
				new_number = 1200
		else:
			# No existing numbers, start from 1200
			new_number = 1200

		# Format as WAXXXXX (5 digits, zero-padded)
		wa_nummer = f"WA{new_number:05d}"

		# Check if this number already exists (safety check)
		while frappe.db.exists("WA Nummer", wa_nummer):
			new_number += 1
			wa_nummer = f"WA{new_number:05d}"

		return wa_nummer

	def validate(self):
		"""Validate WA Nummer record"""
		# Ensure WA Nummer is unique
		if self.wa_nummer:
			existing = frappe.db.exists("WA Nummer", {
				"wa_nummer": self.wa_nummer,
				"name": ["!=", self.name]
			})
			if existing:
				frappe.throw(_("WA Nummer {0} already exists").format(self.wa_nummer))
