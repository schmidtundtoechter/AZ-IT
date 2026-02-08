# File: az_it/az_it/python_scripts/overrides/item_description.py
"""
Auto-prepend item_name to Item description field.

When a new Item is created, this hook automatically prepends the item_name
as a bold heading at the top of the description field, followed by a blank
line and the existing description content.

Requirement: Item descriptions should always start with the item name in bold
for consistency and clarity in documents, invoices, and reports.
"""

import frappe
from bs4 import BeautifulSoup
from frappe.utils import cstr, strip_html, escape_html


def prepend_item_name_to_description(doc, method):
	"""
	Hook: Item.validate

	Prepends the item_name to the description field when creating a new Item.
	Format: <div><p><strong>ITEM_NAME</strong></p><p></p>...existing...</div>

	Args:
		doc: Item document
		method: Hook method name (validate)
	"""
	# Only process new Items
	if not doc.is_new():
		return

	# Skip if no item_name (shouldn't happen, but safety check)
	if not doc.item_name:
		return

	# Skip if description already starts with item_name
	if _description_starts_with_item_name(doc.description, doc.item_name):
		return

	# Prepend item_name to description
	doc.description = _prepend_item_name_html(doc.description, doc.item_name)


def _description_starts_with_item_name(description, item_name):
	"""
	Check if description already starts with the item_name.

	This prevents duplicate prepending if the user manually added it
	or if the hook runs multiple times during validation.

	Args:
		description: HTML or plain text description
		item_name: Item name to check for

	Returns:
		bool: True if description starts with item_name
	"""
	if not description:
		return False

	# Get plain text version
	plain_text = strip_html(cstr(description)).strip()
	item_name_stripped = cstr(item_name).strip()

	# Check if it starts with item_name (case-insensitive for safety)
	return plain_text.lower().startswith(item_name_stripped.lower())


def _prepend_item_name_html(description, item_name):
	"""
	Prepend item_name as bold HTML to the description.

	Handles various description formats:
	- Empty/None: Creates new HTML structure
	- Plain text: Wraps in div>p and prepends item_name
	- HTML: Inserts item_name at the beginning of existing structure

	Args:
		description: Current description (HTML or plain text)
		item_name: Item name to prepend

	Returns:
		str: HTML description with item_name prepended
	"""
	# Handle empty description
	if not description or not strip_html(cstr(description)).strip():
		return f'<div><p><strong>{escape_html(item_name)}</strong></p></div>'

	description = cstr(description).strip()

	# Parse HTML with BeautifulSoup
	soup = BeautifulSoup(description, 'html.parser')

	# Create item_name elements
	strong_tag = soup.new_tag('strong')
	strong_tag.string = item_name

	item_name_p = soup.new_tag('p')
	item_name_p.append(strong_tag)

	blank_line_p = soup.new_tag('p')

	# Find or create wrapper div
	wrapper_div = _find_or_create_wrapper_div(soup, description)

	# Insert item_name paragraph and blank line at the beginning
	wrapper_div.insert(0, blank_line_p)
	wrapper_div.insert(0, item_name_p)

	return str(wrapper_div)


def _find_or_create_wrapper_div(soup, description):
	"""
	Find existing wrapper div or create one.

	ERPNext Text Editor fields typically wrap content in a div.
	This function handles both cases: existing div or plain content.

	Args:
		soup: BeautifulSoup object
		description: Original description string

	Returns:
		BeautifulSoup Tag: div element containing the content
	"""
	# Check if there's already a div wrapper
	existing_div = soup.find('div')

	if existing_div:
		return existing_div

	# No div found - create wrapper and move all content into it
	wrapper_div = soup.new_tag('div')

	# Move all existing content into the div
	# Create a copy of contents to avoid modification during iteration
	contents = list(soup.children)
	for element in contents:
		wrapper_div.append(element.extract())

	soup.append(wrapper_div)
	return wrapper_div
