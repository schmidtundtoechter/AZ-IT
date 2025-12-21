# WA Nummer Feature - Testing & Presentation Guide

## Overview
This guide provides step-by-step instructions for testing and presenting the new WA Nummer (Support Contract Number) feature implemented in the AZ IT app.

---

## 1. Prerequisites

Before testing, ensure:
- The bench is running: `bench start`
- You are logged in to the ERPNext system at http://localhost:8003
- You have the necessary permissions (System Manager, Sales Manager, or Sales User role)

---

## 2. Feature Components Implemented

### A. New DocType: WA Nummer
- Location: DocType List → Search "WA Nummer"
- Fields:
  - **WA Nummer**: Auto-generated (WAXXXXX format, 5-digit sequential)
  - **Kunde**: Link to Customer (required)
  - **Zugehöriger Artikel**: Link to Item (required)
  - **Vertragsabschluss**: Contract conclusion date (auto-filled with today's date)
  - **Auftrag**: Link to Sales Order (required)
  - **Aktueller Preis**: Current price (manually editable)
  - **Alter Preis**: Old price (manually editable)
  - **Kommentar**: Comment field

### B. Custom Fields Added
1. **Customer DocType**: WA Nummer section with HTML field showing all WA Numbers for the customer
2. **Sales Order DocType**: WA Nummer link field (editable after submit)
3. **Sales Invoice DocType**: WA Nummer link field (editable after submit)

---

## 3. Step-by-Step Testing Procedure

### Test 1: Create First WA Nummer Record

1. **Navigate to WA Nummer DocType**
   - Go to: Search bar → Type "WA Nummer" → Click on DocType

2. **Create New Record**
   - Click "+ Add WA Nummer" button
   - You should see a blue info message: "WA Nummer will be automatically generated when you save this record."

3. **Fill Required Fields**
   - **Kunde**: Select any customer (e.g., "Test Customer")
   - **Zugehöriger Artikel**: Select any item (e.g., "Support Contract - Monthly")
   - **Auftrag**: Select any Sales Order
   - **Vertragsabschluss**: Will be auto-filled with today's date (or change if needed)
   - **Aktueller Preis**: Enter any price (e.g., 500.00)

4. **Save the Record**
   - Click "Save"
   - **Expected Result**: WA Nummer field should automatically populate with "WA00001"
   - The document name should also be "WA00001"

5. **Verify Automatic Numbering**
   - Create another WA Nummer record
   - **Expected Result**: The new record should get "WA00002"

---

### Test 2: Customer Integration

1. **Open a Customer**
   - Go to: Customer List → Select any customer that has WA Numbers

2. **Verify WA Nummer Section**
   - Scroll down to find "WA Nummer (Support Contracts)" section
   - **Expected Result**: You should see a table listing all WA Numbers for this customer with:
     - WA Nummer (clickable link)
     - Article
     - Contract Date
     - Current Price
     - Sales Order (clickable link)

3. **Test "View WA Numbers" Button**
   - Click the "View WA Numbers" button in the top right under "Actions"
   - **Expected Result**: Should navigate to WA Nummer list filtered by this customer

4. **Test "Create New WA Nummer" Button**
   - Click the "Create New WA Nummer" button in the top right under "Create"
   - **Expected Result**: Should open a new WA Nummer form with Customer field pre-filled

---

### Test 3: Sales Order Integration

1. **Create a New Sales Order**
   - Go to: Sales Order List → "+ Add Sales Order"
   - Select a Customer
   - Add items and save the order

2. **Test WA Nummer Field**
   - Look for "WA Nummer" field (should be after "PO No" field)
   - Click on the field
   - **Expected Result**: The dropdown should only show WA Numbers for the selected customer

3. **Select a WA Nummer**
   - Select any WA Nummer from the dropdown
   - **Expected Result**: A green alert should appear showing:
     - WA Nummer
     - Article
     - Current Price

4. **Test Editability After Submit**
   - Submit the Sales Order
   - Try to edit the WA Nummer field
   - **Expected Result**: Field should still be editable even after submission

5. **Test "Create WA Nummer" Button**
   - For a submitted Sales Order, you should see a "Create WA Nummer" button
   - Click it
   - **Expected Result**: New WA Nummer form opens with Customer and Auftrag pre-filled

6. **Test Customer Change**
   - In draft Sales Order, change the customer
   - **Expected Result**: WA Nummer field should clear with an orange alert

---

### Test 4: Sales Invoice Integration

1. **Create a New Sales Invoice**
   - Go to: Sales Invoice List → "+ Add Sales Invoice"
   - Select a Customer
   - Add items

2. **Test WA Nummer Field**
   - Look for "WA Nummer" field (should be after "PO No" field)
   - Click on the field
   - **Expected Result**: The dropdown should only show WA Numbers for the selected customer

3. **Select a WA Nummer**
   - Select any WA Nummer from the dropdown
   - **Expected Result**: A green alert should appear showing WA details

4. **Test Editability After Submit**
   - Submit the Sales Invoice
   - Try to edit the WA Nummer field
   - **Expected Result**: Field should still be editable even after submission

5. **Test Customer Change**
   - In draft Sales Invoice, change the customer
   - **Expected Result**: WA Nummer field should clear with an orange alert

---

### Test 5: Unique WA Nummer Validation

1. **Attempt to Create Duplicate**
   - Try to manually override the WA Nummer field with an existing number
   - Try to save
   - **Expected Result**: Should show error "WA Nummer WAXXXXX already exists"

---

### Test 6: WA Nummer Sequence Continuity

1. **Check Current Highest Number**
   - Go to WA Nummer list
   - Sort by WA Nummer descending
   - Note the highest number (e.g., WA00005)

2. **Create New Record**
   - Create a new WA Nummer
   - **Expected Result**: Should get next number (e.g., WA00006)

3. **Test After Data Import** (if applicable)
   - If old WA Numbers are imported with high numbers (e.g., WA12345)
   - Create a new record
   - **Expected Result**: Should get WA12346 (next number after highest)



## 5. Key Points to Highlight

### Automatic Features
- ✅ WA Nummer auto-generated (WAXXXXX format)
- ✅ Unique constraint enforced
- ✅ Sequential numbering maintained
- ✅ Contract date auto-filled

### Integration Features
- ✅ Customer can view all their WA Numbers
- ✅ Quick filters in Sales Order and Sales Invoice
- ✅ Only shows WA Numbers for selected customer
- ✅ Editable after document submission
- ✅ Quick create buttons

### User-Friendly Features
- ✅ Helpful alerts and messages
- ✅ Clickable links between related documents
- ✅ Clear descriptions on fields
- ✅ Auto-clearing when customer changes

