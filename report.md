# QuickCart REST API Black Box Testing Report

This report outlines the black-box testing constructed for the QuickCart REST API, following the requirements provided in the API Documentation. A total of 102 test cases were developed using `requests` and `pytest`. To enhance readability given the large volume of test cases, they have been logically grouped by API resource and test methodology (e.g., valid requests, boundary values, invalid inputs). 

A total of 8 bugs were discovered during testing, which are detailed in the Bug Report section at the end of this document.

---

## 1. Global Authentication / Headers
These tests validate that the API enforces the presence and validity of required headers across endpoints.

| Test Case Group | Inputs | Expected Output | Justification |
| --- | --- | --- | --- |
| **Missing Headers** | Omit `X-Roll-Number` / `X-User-ID` on user endpoints | 400/401 Unauthorized/Bad Request | Validates security enforcement for missing authentication. |
| **Invalid Header Types** | `X-Roll-Number` = "abc", `X-User-ID` = "0", "-1" | 400 Bad Request | Ensures only valid positive integer values are processed. |

---

## 2. Admin & Data Inspection (`/api/v1/admin/*`)
Tests for the admin endpoints which return system-wide active/inactive records, used primarily for test setup and verification.

| Test Case Group | Inputs | Expected Output | Justification |
| --- | --- | --- | --- |
| **Valid Retrieval** | GET requests to `/admin/users`, `/admin/carts`, `/admin/products`, etc. | 200 OK + List of records | Verifies admin endpoints correctly fetch entire database contents without user-scoping. |
| **Response Structure** | GET `/admin/users` | Includes `wallet_balance`, `loyalty_points` | Ensures all expected internal fields are exposed to admins. |
| **Inactive Data Access** | GET `/admin/products` vs GET `/products` | Admin returns $\ge$ user products | Validates admin can see inactive products which users cannot. |

---

## 3. Profile (`/api/v1/profile`)

| Test Case Group | Inputs | Expected Output | Justification |
| --- | --- | --- | --- |
| **Valid Profile Retrieval** | GET `/profile` | 200 OK + Profile Data | Ensures user can fetch their profile. |
| **Valid Boundary Values** | PUT `/profile` with Name length (2, 50 chars) and Phone (10 digits) | 200 OK | Asserts the boundary condition limits are correctly supported. |
| **Invalid Boundary Values** | PUT `/profile` with Name (<2 or >50 chars), Phone (<10 or >10 digits) | 400 Bad Request | Verifies rejection of structurally invalid lengths. |
| **Wrong Data Types** | Phone containing letters (e.g., "123abc7890") | 400 Bad Request | Ensures correct type validation (digits only) for phone numbers. |
| **Immutability of Fields** | PUT payload including `wallet_balance`, `loyalty_points`, `user_id` | 200 OK (Updates profile), but fields remain unchanged | Security validation: ensures users cannot elevate privileges or spoof funds. |

---

## 4. Addresses (`/api/v1/addresses`)

| Test Case Group | Inputs | Expected Output | Justification |
| --- | --- | --- | --- |
| **Valid Creation & Retrieval** | POST `/addresses` with valid payload, GET `/addresses` | 200/201 OK + generated ID & fields | Verifies functional address addition and correct data formatting. |
| **Invalid Field Enum / Length** | POST with Label = `GARAGE`, City <2/>50 chars, Pincode = 5/7 digits | 400 Bad Request | Verifies strict adherence to data requirements and enumerations. |
| **Immutable Updates** | PUT `/addresses/{id}` changing `label`, `city`, `pincode` | 200 OK, but fields remain unchanged | Ensures specific fields cannot be changed post-creation as per docs. |
| **Default Address Exclusivity** | POST multiple addresses with `is_default=True` | Only 1 address is saved as default | Logical validation to ensure state constraints (only one default address allows). |
| **Missing Record Deletion** | DELETE `/addresses/{random_id}` | 404 Not Found | Verifies API properly handles missing resources. |

---

## 5. Products (`/api/v1/products`)

| Test Case Group | Inputs | Expected Output | Justification |
| --- | --- | --- | --- |
| **Active Listing Constraints** | GET `/products` | 200 OK; Only active products returned | Validates privacy rules preventing users from buying inactive products. |
| **Valid Product Lookup** | GET `/products/{valid_id}` | 200 OK + Product Details | Base retrieval functionality. |
| **Invalid Product Lookup** | GET `/products/99999` | 404 Not Found | Base missing resource handling. |
| **Filtering & Searching** | GET `?category=x`, GET `?search=query`, GET `?sort=price_asc`/`desc` | 200 OK + Filtered/Sorted Data | Search accuracy over the product catalog. |
| **Price Accuracy** | Price observed in `/products` vs Database (`/admin/products`) | Exact match | Prevents price manipulation bugs or stale caching on catalog endpoints. |

---

## 6. Cart (`/api/v1/cart`)

| Test Case Group | Inputs | Expected Output | Justification |
| --- | --- | --- | --- |
| **Valid Addition & Accumulation** | POST `/cart/add` (same item twice) | 200 OK; quantity accumulates | Verifies aggregation logic instead of overriding values. |
| **Invalid Zero/Negative Qty** | POST `/cart/add` or `/update` with `quantity` = 0 or -5 | 400 Bad Request | Boundary rules preventing logical paradoxes (negative items). |
| **Missing/Unavailable Stock** | POST `/cart/add` for invalid ID, or qty > available stock | 404 Not Found / 400 Bad Request | Stock validation handling. |
| **Price Tampering Checks** | POST `/cart/add` submitting a fake `price` field | Unit price tracks real DB value | Security validation ensuring malicious input doesn't override real prices. |
| **Mathematical Accuracy** | GET `/cart` check sizes vs `subtotal` & `total` | `subtotal = qty*price`, `total = sum(subtotals)` | Calculation correctness without off-by-one skipping or rounding errors. |

---

## 7. Coupons (`/api/v1/coupon`)

| Test Case Group | Inputs | Expected Output | Justification |
| --- | --- | --- | --- |
| **Applying Expired Coupon** | POST `/coupon/apply` with expired code | 400 Bad Request | Validates expiration triggers. |
| **Minimum Bound Check** | Cart total < `min_cart_value` | 400 Bad Request | Enforces minimum spend logic. |
| **Discount Calculation Types** | FIXED vs PERCENT coupon codes applied to cart | Calculated discount accurately subtracted subject to cap | Assures business math requirements regarding discounts. |

---

## 8. Checkout (`/api/v1/checkout`)

| Test Case Group | Inputs | Expected Output | Justification |
| --- | --- | --- | --- |
| **Empty Cart & Fake Payment** | POST `/checkout` with empty cart or `payment_method` = "BITCOIN" | 400 Bad Request | Core transactional constraints. |
| **COD Absolute Limits** | POST `/checkout` with COD if cart total > 5000 | 400 Bad Request | Verifies boundary cap on specific payment methods. |
| **Payment Status Mapping** | Initial state mapping for CARD vs COD/WALLET | CARD -> PAID, COD/WALLET -> PENDING | Payment state machine logic. |

---

## 9. Wallet & Loyalty (`/api/v1/wallet`, `/api/v1/loyalty`)

| Test Case Group | Inputs | Expected Output | Justification |
| --- | --- | --- | --- |
| **Wallet Adding Boundaries** | POST `/wallet/add` amounts: -1, 0, 100001 | 400 Bad Request | Upper and lower boundaries for reloading wallets. |
| **Valid Payment & Balances** | POST `/wallet/pay` deduction | Exact amount deducted from balance | Validates fund arithmetic and exact transfer amounts. |
| **Insufficient Funds** | Deducting > available balance / Redeeming > available points | 400 Bad Request | Verification of overdraft constraints. |
| **Loyalty Boundaries** | Redeeming 0 or negative points | 400 Bad Request | Prevents logical circumvention of point deductions. |

---

## 10. Orders & Reviews & Support Tickets

| Test Case Group | Inputs | Expected Output | Justification |
| --- | --- | --- | --- |
| **Order Cancellation Validations** | Cancelling DELIVERED/Non-existent orders | 400 Bad Request / 404 Not Found | Forward-only state validation. |
| **Order Stock Restoration** | POST `/orders/{id}/cancel` | `stock += qty` | Inventory integrity maintenance post transaction. |
| **Invoice Correctness** | GET `/orders/{id}/invoice` | Subtotal, GST, Total match | Ensures taxation calculations are compliant with specifications. |
| **Review Boundaries** | POST `/products/{id}/reviews` with rating 0, 6, empty body, >200 chars | 400 Bad Request | Ensures rating and text bounds limits. |
| **Averaging Logic** | GET `/products/{id}/reviews` with mixed reviews | Proper decimal calculation | Validates math representation for averages avoiding truncation. |
| **Ticket Status State Map** | Valid/Invalid transitions (OPEN -> CLOSED, etc) | Validates transitions strict path (OPEN->IN_PROGRESS->CLOSED) | Directed acyclic graph enforcement for helpdesk items. |
| **Ticket Immutability** | PUT `/support/tickets/{id}` modifying subject/message | Updates status, leaves text unchanged | Prevents users modifying historical reports covertly. |

---

## Bug Report

During the black-box testing phase, 8 functional bugs were uncovered relating directly to violations of the API documentation rules.

### Bug 1: Cart accepts Zero Quantity
- **Endpoint Tested**: `POST /api/v1/cart/add`
- **Request Payload**: 
  - Method: `POST`
  - URL: `/api/v1/cart/add`
  - Headers: `X-Roll-Number: <roll>`, `X-User-ID: <id>`, `Content-Type: application/json`
  - Body: `{"product_id": 1, "quantity": 0}`
- **Expected Result**: 400 Bad Request. (Documentation explicitly states quantity must be at least 1).
- **Actual Result**: 200 OK. The server permitted adding an item with a zero quantity.

### Bug 2: Cart accepts Negative Quantity
- **Endpoint Tested**: `POST /api/v1/cart/add`
- **Request Payload**:
  - Method: `POST`
  - URL: `/api/v1/cart/add`
  - Headers: `X-Roll-Number: <roll>`, `X-User-ID: <id>`, `Content-Type: application/json`
  - Body: `{"product_id": 1, "quantity": -5}`
- **Expected Result**: 400 Bad Request.
- **Actual Result**: 200 OK. The server permitted adding an item with a negative quantity.

### Bug 3: Missing Review Rating Boundary Validation
- **Endpoint Tested**: `POST /api/v1/products/{product_id}/reviews`
- **Request Payload**:
  - Method: `POST`
  - URL: `/api/v1/products/1/reviews`
  - Headers: `X-Roll-Number: <roll>`, `X-User-ID: <id>`, `Content-Type: application/json`
  - Body: `{"rating": 0, "comment": "Good"}`
- **Expected Result**: 400 Bad Request. (Documentation specifies rating must be between 1 and 5).
- **Actual Result**: 200 OK. The server accepted a rating of 0 (and later 6).

### Bug 4: Inadequate Validation on Phone Number Characters
- **Endpoint Tested**: `PUT /api/v1/profile`
- **Request Payload**:
  - Method: `PUT`
  - URL: `/api/v1/profile`
  - Headers: `X-Roll-Number: <roll>`, `X-User-ID: <id>`, `Content-Type: application/json`
  - Body: `{"name": "ValidName", "phone": "123abc7890"}`
- **Expected Result**: 400 Bad Request. (Telephone requires 10 digits implicitly, alphabets are invalid).
- **Actual Result**: 200 OK. Server processes the alphabet characters inside the phone number.

### Bug 5: Default Address Exclusivity Not Enforced
- **Endpoint Tested**: `POST /api/v1/addresses`
- **Request Payload**:
  - Method: `POST`
  - URL: `/api/v1/addresses`
  - Headers: `X-Roll-Number: <roll>`, `X-User-ID: <id>`, `Content-Type: application/json`
  - Body: `{"label": "OFFICE", "street": "Default Street Two", "city": "CityB", "pincode": "333444", "is_default": true}` (fired after already creating another default)
- **Expected Result**: Setting a new address to default must safely clear the `is_default` flag on all existing addresses, such that only 1 address is default at any time.
- **Actual Result**: Multiple addresses end up having `is_default: true` simultaneously.

### Bug 6: Product Prices Mismatch Admin vs User Views
- **Endpoint Tested**: `GET /api/v1/products`
- **Request Payload**:
  - Method: `GET`
  - URL: `/api/v1/products`
  - Headers: `X-Roll-Number: <roll>`, `X-User-ID: <id>`
  - Body: None
- **Expected Result**: The price shown in the user product list must perfectly match the exact real price stored in the database / visible to administrators (`/admin/products`).
- **Actual Result**: The price values differ between what users observe and the real system values (indicates caching error or unintended markup logic).

### Bug 7: Incorrect GST Calculation on Invoices
- **Endpoint Tested**: `GET /api/v1/orders/{order_id}/invoice`
- **Request Payload**:
  - Method: `GET`
  - URL: `/api/v1/orders/{order_id}/invoice`
  - Headers: `X-Roll-Number: <roll>`, `X-User-ID: <id>`
  - Body: None
- **Expected Result**: `gst_amount` must mathematically map exactly to $5\%$ of the `subtotal`.
- **Actual Result**: The reported `gst_amount` computed is incorrect and does not reflect $5\%$ of the subtotal logic.

### Bug 8: Order Cancellation Leaves Stock Depleted
- **Endpoint Tested**: `POST /api/v1/orders/{order_id}/cancel`
- **Request Payload**:
  - Method: `POST`
  - URL: `/api/v1/orders/{order_id}/cancel`
  - Headers: `X-Roll-Number: <roll>`, `X-User-ID: <id>`
  - Body: None
- **Expected Result**: Successfully cancelling an order must restore the quantity of cancelled items back into valid active store inventory stock levels.
- **Actual Result**: Stock is not restored after confirmation of cancellation, causing an overall loss of system inventory.

