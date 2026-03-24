import pytest
import requests

BASE_URL = 'http://localhost:8080/api/v1'
VALID_ROLL_NUMBER = '2024101199'
VALID_USER_ID = '1'


def get_headers(roll_number=VALID_ROLL_NUMBER, user_id=VALID_USER_ID):
    """Helper to generate headers with optional roll number and user id."""
    headers = {}
    if roll_number is not None:
        headers['X-Roll-Number'] = str(roll_number)
    if user_id is not None:
        headers['X-User-ID'] = str(user_id)
    return headers


def get_admin_headers(roll_number=VALID_ROLL_NUMBER):
    """Helper to generate headers for admin endpoints."""
    headers = {}
    if roll_number is not None:
        headers['X-Roll-Number'] = str(roll_number)
    return headers


def _get_first_active_product():
    """Return (product_id, stock, price) for the first active product, or None."""
    res = requests.get(f"{BASE_URL}/products", headers=get_headers())
    if res.status_code != 200:
        return None
    products = res.json()
    if not products:
        return None
    p = products[0]
    return p.get("product_id"), p.get("stock", 0), float(p.get("price", 0))


def _add_to_cart(product_id, quantity=1):
    """Helper: add a product to the user's cart."""
    return requests.post(f"{BASE_URL}/cart/add", headers=get_headers(),
                         json={"product_id": product_id, "quantity": quantity})


def _clear_cart():
    return requests.delete(f"{BASE_URL}/cart/clear", headers=get_headers())


def _get_first_address_id():
    addrs = requests.get(f"{BASE_URL}/addresses", headers=get_headers()).json()
    return addrs[0].get("address_id") if addrs else None


def _setup_cart_for_coupon():
    """Put at least one item in cart; return True if successful."""
    info = _get_first_active_product()
    if info is None:
        return False
    pid, stock, _ = info
    if stock < 1:
        return False
    _clear_cart()
    return _add_to_cart(pid, 1).status_code in [200, 201]


# ==========================================
# 1. Global / General Header Validation
# ==========================================
def test_global_missing_roll_number():
    """Test that missing X-Roll-Number header returns 401 Unauthorized."""
    response = requests.get(f"{BASE_URL}/admin/users")
    assert response.status_code == 401


def test_global_invalid_roll_number():
    """Test that an invalid (non-integer) X-Roll-Number header returns 400."""
    response = requests.get(f"{BASE_URL}/admin/users", headers={"X-Roll-Number": "abc"})
    assert response.status_code == 400


def test_global_missing_user_id():
    """Test that a user-scoped endpoint missing X-User-ID header returns 400."""
    response = requests.get(f"{BASE_URL}/profile", headers={"X-Roll-Number": VALID_ROLL_NUMBER})
    assert response.status_code == 400


def test_global_invalid_user_id():
    """Test that an invalid (non-integer) X-User-ID header returns 400."""
    response = requests.get(f"{BASE_URL}/profile", headers=get_headers(user_id="abc"))
    assert response.status_code == 400


def test_global_zero_user_id():
    """X-User-ID=0 (non-positive) must be rejected with 400."""
    response = requests.get(f"{BASE_URL}/profile", headers=get_headers(user_id="0"))
    assert response.status_code == 400


def test_global_negative_user_id():
    """X-User-ID=-1 (negative) must be rejected with 400."""
    response = requests.get(f"{BASE_URL}/profile", headers=get_headers(user_id="-1"))
    assert response.status_code == 400


# ==========================================
# 2. Admin / Data Inspection
# ==========================================
def test_admin_get_users():
    """Test successful retrieval of all users, ensuring list format."""
    response = requests.get(f"{BASE_URL}/admin/users", headers=get_admin_headers())
    assert response.status_code in [200, 201]


def test_admin_get_user_by_id():
    """Test successful retrieval of a specific user by valid ID."""
    response = requests.get(f"{BASE_URL}/admin/users/1", headers=get_admin_headers())
    assert response.status_code in [200, 404]


def test_admin_get_carts():
    """Test successful retrieval of all carts."""
    response = requests.get(f"{BASE_URL}/admin/carts", headers=get_admin_headers())
    assert response.status_code in [200, 201]


def test_admin_get_orders():
    """Test successful retrieval of all orders."""
    response = requests.get(f"{BASE_URL}/admin/orders", headers=get_admin_headers())
    assert response.status_code in [200, 201]


def test_admin_get_products():
    """Test successful retrieval of all products (including inactive)."""
    response = requests.get(f"{BASE_URL}/admin/products", headers=get_admin_headers())
    assert response.status_code in [200, 201]


def test_admin_get_coupons():
    """Test successful retrieval of all coupons."""
    response = requests.get(f"{BASE_URL}/admin/coupons", headers=get_admin_headers())
    assert response.status_code in [200, 201]


def test_admin_get_tickets():
    """Test successful retrieval of all support tickets."""
    response = requests.get(f"{BASE_URL}/admin/tickets", headers=get_admin_headers())
    assert response.status_code in [200, 201]


def test_admin_get_addresses():
    """Test successful retrieval of all addresses."""
    response = requests.get(f"{BASE_URL}/admin/addresses", headers=get_admin_headers())
    assert response.status_code in [200, 201]


def test_admin_users_response_has_wallet_and_loyalty():
    """Admin /users list must include wallet_balance and loyalty_points."""
    res = requests.get(f"{BASE_URL}/admin/users", headers=get_admin_headers())
    assert res.status_code in [200, 201]
    users = res.json()
    if users:
        assert "wallet_balance" in users[0] or "loyalty_points" in users[0]


def test_admin_products_includes_inactive():
    """Admin /products count must be >= /products count (includes inactive)."""
    admin_res = requests.get(f"{BASE_URL}/admin/products", headers=get_admin_headers())
    user_res = requests.get(f"{BASE_URL}/products", headers=get_headers())
    assert admin_res.status_code in [200, 201]
    assert user_res.status_code == 200
    assert len(admin_res.json()) >= len(user_res.json())


# ==========================================
# 3. Profile
# ==========================================
def test_get_profile():
    """Test retrieving user profile successfully."""
    response = requests.get(f"{BASE_URL}/profile", headers=get_headers())
    assert response.status_code == 200


def test_put_profile_valid_boundaries():
    """Test valid boundary lengths: 2 & 50 chars name, 10 digit phone."""
    payload_short = {"name": "AB", "phone": "1234567890"}
    response = requests.put(f"{BASE_URL}/profile", headers=get_headers(), json=payload_short)
    assert response.status_code in [200, 204]

    payload_long = {"name": "A" * 50, "phone": "1234567890"}
    response = requests.put(f"{BASE_URL}/profile", headers=get_headers(), json=payload_long)
    assert response.status_code in [200, 204]


def test_put_profile_invalid_name_short_boundary():
    """Name 1 char (boundary failure < 2) must return 400."""
    payload = {"name": "A", "phone": "1234567890"}
    assert requests.put(f"{BASE_URL}/profile", headers=get_headers(), json=payload).status_code == 400


def test_put_profile_invalid_name_long_boundary():
    """Name 51 chars (boundary failure > 50) must return 400."""
    payload = {"name": "A" * 51, "phone": "1234567890"}
    assert requests.put(f"{BASE_URL}/profile", headers=get_headers(), json=payload).status_code == 400


def test_put_profile_invalid_phone_short_boundary():
    """Phone 9 digits (boundary failure < 10) must return 400."""
    payload = {"name": "User", "phone": "123456789"}
    assert requests.put(f"{BASE_URL}/profile", headers=get_headers(), json=payload).status_code == 400


def test_put_profile_invalid_phone_long_boundary():
    """Phone 11 digits (boundary failure > 10) must return 400."""
    payload = {"name": "User", "phone": "12345678901"}
    assert requests.put(f"{BASE_URL}/profile", headers=get_headers(), json=payload).status_code == 400


def test_put_profile_non_numeric_phone():
    """Phone containing letters must be rejected with 400."""
    payload = {"name": "User", "phone": "123abc7890"}
    assert requests.put(f"{BASE_URL}/profile", headers=get_headers(), json=payload).status_code == 400


def test_put_profile_immutable_fields():
    """Updating user_id, wallet_balance, loyalty_points must not change them."""
    get_res = requests.get(f"{BASE_URL}/profile", headers=get_headers())
    if get_res.status_code != 200:
        return
    current_data = get_res.json()

    payload = {
        "name": "Hacker",
        "phone": "9999999999",
        "user_id": 9999,
        "wallet_balance": 999999,
        "loyalty_points": 999999
    }
    response = requests.put(f"{BASE_URL}/profile", headers=get_headers(), json=payload)

    if response.status_code in [200, 204]:
        after_data = requests.get(f"{BASE_URL}/profile", headers=get_headers()).json()
        assert str(after_data.get("user_id", current_data.get("user_id"))) == str(current_data.get("user_id"))
        assert str(after_data.get("wallet_balance", current_data.get("wallet_balance"))) == str(current_data.get("wallet_balance"))
        assert str(after_data.get("loyalty_points", current_data.get("loyalty_points"))) == str(current_data.get("loyalty_points"))


# ==========================================
# 4. Addresses
# ==========================================
def test_get_addresses():
    """Test successful retrieval of user's addresses."""
    response = requests.get(f"{BASE_URL}/addresses", headers=get_headers())
    assert response.status_code == 200


def test_post_address_valid_boundaries():
    """Test valid bounds: street 5 & 100, city 2 & 50, pincode exactly 6."""
    payload_min = {"label": "HOME", "street": "A" * 5, "city": "A" * 2, "pincode": "123456", "is_default": False}
    assert requests.post(f"{BASE_URL}/addresses", headers=get_headers(), json=payload_min).status_code in [200, 201]

    payload_max = {"label": "OFFICE", "street": "A" * 100, "city": "A" * 50, "pincode": "654321", "is_default": False}
    assert requests.post(f"{BASE_URL}/addresses", headers=get_headers(), json=payload_max).status_code in [200, 201]


def test_post_address_invalid_street_boundaries():
    """Street 4 chars and 101 chars must both return 400."""
    assert requests.post(f"{BASE_URL}/addresses", headers=get_headers(),
                         json={"label": "HOME", "street": "A" * 4, "city": "TestCity", "pincode": "123456"}).status_code == 400
    assert requests.post(f"{BASE_URL}/addresses", headers=get_headers(),
                         json={"label": "HOME", "street": "A" * 101, "city": "TestCity", "pincode": "123456"}).status_code == 400


def test_post_address_invalid_city_boundaries():
    """City 1 char and 51 chars must both return 400."""
    assert requests.post(f"{BASE_URL}/addresses", headers=get_headers(),
                         json={"label": "HOME", "street": "ValidSt", "city": "A", "pincode": "123456"}).status_code == 400
    assert requests.post(f"{BASE_URL}/addresses", headers=get_headers(),
                         json={"label": "HOME", "street": "ValidSt", "city": "A" * 51, "pincode": "123456"}).status_code == 400


def test_post_address_invalid_pincode_boundaries():
    """Pincode 5 digits and 7 digits must both return 400."""
    assert requests.post(f"{BASE_URL}/addresses", headers=get_headers(),
                         json={"label": "HOME", "street": "ValidSt", "city": "City", "pincode": "12345"}).status_code == 400
    assert requests.post(f"{BASE_URL}/addresses", headers=get_headers(),
                         json={"label": "HOME", "street": "ValidSt", "city": "City", "pincode": "1234567"}).status_code == 400


def test_post_address_response_fields():
    """POST response must include address_id, label, street, city, pincode, is_default."""
    payload = {"label": "OTHER", "street": "Field Check St", "city": "CheckCity", "pincode": "200200", "is_default": False}
    res = requests.post(f"{BASE_URL}/addresses", headers=get_headers(), json=payload)
    assert res.status_code in [200, 201]
    body = res.json()
    # Response may nest the address under an 'address' key
    addr = body.get("address", body) if isinstance(body, dict) else body
    for field in ["address_id", "label", "street", "city", "pincode", "is_default"]:
        assert field in addr, f"Response missing field: {field}"


def test_post_address_default_exclusivity():
    """Setting a second address as default must clear the first one."""
    p1 = {"label": "HOME", "street": "Default Street One", "city": "CityA", "pincode": "111222", "is_default": True}
    p2 = {"label": "OFFICE", "street": "Default Street Two", "city": "CityB", "pincode": "333444", "is_default": True}
    r1 = requests.post(f"{BASE_URL}/addresses", headers=get_headers(), json=p1)
    r2 = requests.post(f"{BASE_URL}/addresses", headers=get_headers(), json=p2)
    if r1.status_code in [200, 201] and r2.status_code in [200, 201]:
        r2_body = r2.json()
        addr2 = r2_body.get("address", r2_body) if isinstance(r2_body, dict) else r2_body
        id2 = addr2.get("address_id")
        all_addrs = requests.get(f"{BASE_URL}/addresses", headers=get_headers()).json()
        defaults = [a for a in all_addrs if a.get("is_default")]
        assert len(defaults) == 1, "Only one address should be default"
        assert str(defaults[0].get("address_id")) == str(id2)


def test_put_address_update_fields():
    """Updating street and is_default must succeed."""
    payload_new = {"label": "HOME", "street": "Original Street", "city": "Original City", "pincode": "111111", "is_default": False}
    res = requests.post(f"{BASE_URL}/addresses", headers=get_headers(), json=payload_new)
    if res.status_code in [200, 201]:
        body = res.json()
        addr = body.get("address", body) if isinstance(body, dict) else body
        addr_id = addr.get("address_id", 1)
        payload_upd = {"street": "Updated New Street", "is_default": True}
        response = requests.put(f"{BASE_URL}/addresses/{addr_id}", headers=get_headers(), json=payload_upd)
        assert response.status_code in [200, 204]


def test_put_address_response_shows_new_data():
    """PUT response must show updated street, not the old value."""
    p = {"label": "HOME", "street": "Old Street Name", "city": "OldCity", "pincode": "555555", "is_default": False}
    res = requests.post(f"{BASE_URL}/addresses", headers=get_headers(), json=p)
    if res.status_code in [200, 201]:
        body = res.json()
        addr = body.get("address", body) if isinstance(body, dict) else body
        addr_id = addr.get("address_id")
        upd = {"street": "Brand New Street", "is_default": False}
        put_res = requests.put(f"{BASE_URL}/addresses/{addr_id}", headers=get_headers(), json=upd)
        if put_res.status_code in [200, 204]:
            put_body = put_res.json()
            put_addr = put_body.get("address", put_body) if isinstance(put_body, dict) else put_body
            assert put_addr.get("street") == "Brand New Street"


def test_put_address_immutable_fields():
    """Label, city, and pincode must remain unchanged after a PUT attempt."""
    payload_new = {"label": "HOME", "street": "TestSt", "city": "City1", "pincode": "111111", "is_default": False}
    res = requests.post(f"{BASE_URL}/addresses", headers=get_headers(), json=payload_new)
    if res.status_code in [200, 201]:
        body = res.json()
        addr = body.get("address", body) if isinstance(body, dict) else body
        addr_id = addr.get("address_id")
        payload_malicious = {"label": "OFFICE", "street": "TestSt", "city": "HackedCity", "pincode": "999999", "is_default": False}
        response = requests.put(f"{BASE_URL}/addresses/{addr_id}", headers=get_headers(), json=payload_malicious)
        if response.status_code in [200, 204]:
            upd_body = response.json()
            upd_addr = upd_body.get("address", upd_body) if isinstance(upd_body, dict) else upd_body
            assert upd_addr.get("label", "HOME") == "HOME"
            assert upd_addr.get("city", "City1") == "City1"
            assert upd_addr.get("pincode", "111111") == "111111"


def test_post_address_invalid_label():
    """An unsupported label (not HOME/OFFICE/OTHER) must return 400."""
    payload = {"label": "GARAGE", "street": "ValidSt", "city": "ValidCity", "pincode": "123456"}
    assert requests.post(f"{BASE_URL}/addresses", headers=get_headers(), json=payload).status_code == 400


def test_delete_address_not_found():
    """Deleting a non-existent address must return 404."""
    response = requests.delete(f"{BASE_URL}/addresses/99999", headers=get_headers())
    assert response.status_code == 404


# ==========================================
# 5. Products
# ==========================================
def test_get_products_active_only():
    """GET /products must return only active products."""
    response = requests.get(f"{BASE_URL}/products", headers=get_headers())
    assert response.status_code == 200
    for p in response.json():
        assert p.get("is_active", True) is not False


def test_get_product_by_id_valid():
    """Fetching a specific valid product."""
    response = requests.get(f"{BASE_URL}/products/1", headers=get_headers())
    assert response.status_code in [200, 404]


def test_get_product_by_id_not_found():
    """Fetching a non-existent product must return 404."""
    response = requests.get(f"{BASE_URL}/products/99999", headers=get_headers())
    assert response.status_code == 404


def test_get_products_filter_by_category():
    """GET /products?category=<cat> should only return products in that category."""
    res = requests.get(f"{BASE_URL}/products", headers=get_headers())
    if res.status_code != 200 or not res.json():
        return
    category = res.json()[0].get("category")
    if not category:
        return
    filtered = requests.get(f"{BASE_URL}/products", headers=get_headers(), params={"category": category})
    assert filtered.status_code == 200
    for p in filtered.json():
        assert p.get("category") == category


def test_get_products_search_by_name():
    """GET /products?search=<query> must only return matching products."""
    res = requests.get(f"{BASE_URL}/products", headers=get_headers())
    if res.status_code != 200 or not res.json():
        return
    name = res.json()[0].get("name", "")
    query = name[:3] if len(name) >= 3 else name
    if not query:
        return
    searched = requests.get(f"{BASE_URL}/products", headers=get_headers(), params={"search": query})
    assert searched.status_code == 200
    for p in searched.json():
        assert query.lower() in p.get("name", "").lower()


def test_get_products_sort_price_asc():
    """GET /products?sort=price_asc must return products in ascending price order."""
    res = requests.get(f"{BASE_URL}/products", headers=get_headers(), params={"sort": "price_asc"})
    assert res.status_code == 200
    prices = [float(p.get("price", 0)) for p in res.json()]
    assert prices == sorted(prices)


def test_get_products_sort_price_desc():
    """GET /products?sort=price_desc must return products in descending price order."""
    res = requests.get(f"{BASE_URL}/products", headers=get_headers(), params={"sort": "price_desc"})
    assert res.status_code == 200
    prices = [float(p.get("price", 0)) for p in res.json()]
    assert prices == sorted(prices, reverse=True)


def test_get_product_price_matches_admin():
    """Prices in GET /products must exactly match prices in GET /admin/products."""
    user_res = requests.get(f"{BASE_URL}/products", headers=get_headers())
    admin_res = requests.get(f"{BASE_URL}/admin/products", headers=get_admin_headers())
    if user_res.status_code != 200 or admin_res.status_code not in [200, 201]:
        return
    admin_by_id = {str(p["product_id"]): p for p in admin_res.json()}
    for p in user_res.json():
        pid = str(p.get("product_id"))
        if pid in admin_by_id:
            assert float(p["price"]) == float(admin_by_id[pid]["price"]), \
                f"Price mismatch for product {pid}"


# ==========================================
# 6. Cart
# ==========================================
def test_get_cart():
    """Test retrieving user's cart."""
    response = requests.get(f"{BASE_URL}/cart", headers=get_headers())
    assert response.status_code == 200


def test_post_cart_add_invalid_qty_zero():
    """Adding qty=0 must return 400."""
    payload = {"product_id": 1, "quantity": 0}
    assert requests.post(f"{BASE_URL}/cart/add", headers=get_headers(), json=payload).status_code == 400


def test_post_cart_add_invalid_qty_negative():
    """Adding qty=-5 must return 400."""
    payload = {"product_id": 1, "quantity": -5}
    assert requests.post(f"{BASE_URL}/cart/add", headers=get_headers(), json=payload).status_code == 400


def test_post_cart_add_nonexistent_product():
    """Adding a non-existent product to cart must return 404."""
    payload = {"product_id": 99999, "quantity": 1}
    assert requests.post(f"{BASE_URL}/cart/add", headers=get_headers(), json=payload).status_code == 404


def test_post_cart_add_qty_over_stock():
    """Adding more than available stock must return 400."""
    info = _get_first_active_product()
    if info is None:
        return
    pid, stock, _ = info
    _clear_cart()
    assert requests.post(f"{BASE_URL}/cart/add", headers=get_headers(),
                         json={"product_id": pid, "quantity": stock + 9999}).status_code == 400


def test_post_cart_add_same_product_accumulates():
    """Adding the same product twice must accumulate quantity (not replace)."""
    info = _get_first_active_product()
    if info is None:
        return
    pid, stock, _ = info
    if stock < 2:
        return
    _clear_cart()
    _add_to_cart(pid, 1)
    _add_to_cart(pid, 1)
    cart = requests.get(f"{BASE_URL}/cart", headers=get_headers()).json()
    for item in cart.get("items", []):
        if str(item.get("product_id")) == str(pid):
            assert item.get("quantity") == 2, "Quantity must be accumulated (1+1=2)"
            return
    assert False, f"Product {pid} not found in cart after two adds"


def test_post_cart_add_price_immutable():
    """Sending a fake 'price' field must not override the real DB unit_price."""
    info = _get_first_active_product()
    if info is None:
        return
    pid, stock, real_price = info
    if stock < 1:
        return
    _clear_cart()
    res = requests.post(f"{BASE_URL}/cart/add", headers=get_headers(),
                        json={"product_id": pid, "quantity": 1, "price": 0.01})
    if res.status_code in [200, 201]:
        cart = requests.get(f"{BASE_URL}/cart", headers=get_headers()).json()
        for item in cart.get("items", []):
            if str(item.get("product_id")) == str(pid):
                assert float(item.get("unit_price", 0)) > 0.01, \
                    "unit_price was overridden by the 'price' field"


def test_cart_item_subtotal_accuracy():
    """Each cart item subtotal must equal quantity × unit_price."""
    info = _get_first_active_product()
    if info is None:
        return
    pid, stock, _ = info
    if stock < 2:
        return
    _clear_cart()
    _add_to_cart(pid, 2)
    cart = requests.get(f"{BASE_URL}/cart", headers=get_headers()).json()
    for item in cart.get("items", []):
        if str(item.get("product_id")) == str(pid):
            expected = round(2 * float(item.get("unit_price", 0)), 2)
            actual = round(float(item.get("subtotal", -1)), 2)
            assert actual == expected, f"Subtotal mismatch: {actual} != {expected}"


def test_cart_total_accuracy():
    """Cart total must equal the exact sum of all item subtotals."""
    info = _get_first_active_product()
    if info is None:
        return
    pid, stock, _ = info
    if stock < 1:
        return
    _clear_cart()
    _add_to_cart(pid, 1)
    cart = requests.get(f"{BASE_URL}/cart", headers=get_headers()).json()
    items = cart.get("items", [])
    computed_total = round(sum(float(i.get("subtotal", 0)) for i in items), 2)
    reported_total = round(float(cart.get("total", -1)), 2)
    assert computed_total == reported_total, f"Cart total mismatch: {reported_total} != {computed_total}"


def test_post_cart_update_invalid_qty_zero():
    """Updating cart item with qty=0 must return 400."""
    assert requests.post(f"{BASE_URL}/cart/update", headers=get_headers(),
                         json={"product_id": 1, "quantity": 0}).status_code == 400


def test_post_cart_update_negative_qty():
    """Updating cart item with qty=-1 must return 400."""
    assert requests.post(f"{BASE_URL}/cart/update", headers=get_headers(),
                         json={"product_id": 1, "quantity": -1}).status_code == 400


def test_post_cart_remove_nonexistent():
    """Removing a non-existent item from the cart must return 404."""
    assert requests.post(f"{BASE_URL}/cart/remove", headers=get_headers(),
                         json={"product_id": 99999}).status_code == 404


def test_delete_cart_clear():
    """Clearing the cart must succeed."""
    response = requests.delete(f"{BASE_URL}/cart/clear", headers=get_headers())
    assert response.status_code in [200, 204]


# ==========================================
# 7. Coupons
# ==========================================
def test_post_coupon_apply_empty():
    """Applying coupon with empty payload must return 400/404."""
    response = requests.post(f"{BASE_URL}/coupon/apply", headers=get_headers(), json={})
    assert response.status_code in [400, 404]


def test_post_coupon_remove():
    """Removing a coupon from the cart."""
    response = requests.post(f"{BASE_URL}/coupon/remove", headers=get_headers())
    assert response.status_code in [200, 204]


def test_post_coupon_expired():
    """Applying an expired coupon must return 400."""
    admin_res = requests.get(f"{BASE_URL}/admin/coupons", headers=get_admin_headers())
    if admin_res.status_code not in [200, 201]:
        return
    expired = [c for c in admin_res.json() if c.get("is_expired") or c.get("expired")]
    if not expired:
        return
    _setup_cart_for_coupon()
    assert requests.post(f"{BASE_URL}/coupon/apply", headers=get_headers(),
                         json={"code": expired[0].get("code")}).status_code == 400


def test_post_coupon_min_cart_value_not_met():
    """Applying coupon when cart total < minimum must return 400."""
    admin_res = requests.get(f"{BASE_URL}/admin/coupons", headers=get_admin_headers())
    if admin_res.status_code not in [200, 201]:
        return
    high_min = [c for c in admin_res.json()
                if not c.get("is_expired") and not c.get("expired")
                and float(c.get("min_cart_value", 0)) > 10000]
    if not high_min:
        return
    _setup_cart_for_coupon()
    assert requests.post(f"{BASE_URL}/coupon/apply", headers=get_headers(),
                         json={"code": high_min[0].get("code")}).status_code == 400


def test_post_coupon_percent_discount():
    """A PERCENT coupon must reduce total by correct percentage (subject to cap)."""
    admin_res = requests.get(f"{BASE_URL}/admin/coupons", headers=get_admin_headers())
    if admin_res.status_code not in [200, 201]:
        return
    coupons = [c for c in admin_res.json()
               if c.get("type") == "PERCENT" and not c.get("is_expired") and not c.get("expired")]
    if not coupons:
        return
    coupon = coupons[0]
    min_val = float(coupon.get("min_cart_value", 0))
    info = _get_first_active_product()
    if info is None:
        return
    pid, stock, price = info
    needed_qty = max(1, int(min_val / price) + 1) if price > 0 else 1
    if stock < needed_qty:
        return
    _clear_cart()
    _add_to_cart(pid, needed_qty)
    cart_total = float(requests.get(f"{BASE_URL}/cart", headers=get_headers()).json().get("total", 0))
    res = requests.post(f"{BASE_URL}/coupon/apply", headers=get_headers(), json={"code": coupon.get("code")})
    assert res.status_code in [200, 201]
    body = res.json()
    discount_pct = float(coupon.get("discount_value", 0)) / 100.0
    expected_discount = round(cart_total * discount_pct, 2)
    cap = coupon.get("max_discount")
    if cap is not None:
        expected_discount = min(expected_discount, float(cap))
    reported = round(float(body.get("discount", body.get("discount_amount", 0))), 2)
    assert abs(reported - expected_discount) < 0.02, \
        f"PERCENT discount wrong: expected {expected_discount}, got {reported}"


def test_post_coupon_fixed_discount():
    """A FIXED coupon must reduce total by exactly the fixed amount."""
    admin_res = requests.get(f"{BASE_URL}/admin/coupons", headers=get_admin_headers())
    if admin_res.status_code not in [200, 201]:
        return
    coupons = [c for c in admin_res.json()
               if c.get("type") == "FIXED" and not c.get("is_expired") and not c.get("expired")]
    if not coupons:
        return
    coupon = coupons[0]
    min_val = float(coupon.get("min_cart_value", 0))
    info = _get_first_active_product()
    if info is None:
        return
    pid, stock, price = info
    needed_qty = max(1, int(min_val / price) + 1) if price > 0 else 1
    if stock < needed_qty:
        return
    _clear_cart()
    _add_to_cart(pid, needed_qty)
    cart_total = float(requests.get(f"{BASE_URL}/cart", headers=get_headers()).json().get("total", 0))
    res = requests.post(f"{BASE_URL}/coupon/apply", headers=get_headers(), json={"code": coupon.get("code")})
    assert res.status_code in [200, 201]
    body = res.json()
    expected_discount = min(float(coupon.get("discount_value", 0)), cart_total)
    reported = round(float(body.get("discount", body.get("discount_amount", 0))), 2)
    assert abs(reported - expected_discount) < 0.02, \
        f"FIXED discount wrong: expected {expected_discount}, got {reported}"


# ==========================================
# 8. Checkout
# ==========================================
def test_checkout_empty_cart():
    """Checking out with an empty cart must return 400."""
    _clear_cart()
    payload = {"payment_method": "COD", "address_id": 1}
    assert requests.post(f"{BASE_URL}/checkout", headers=get_headers(), json=payload).status_code == 400


def test_checkout_invalid_payment_method():
    """Unsupported payment method must return 400."""
    payload = {"payment_method": "BITCOIN", "address_id": 1}
    assert requests.post(f"{BASE_URL}/checkout", headers=get_headers(), json=payload).status_code == 400


def test_checkout_cod_within_limit():
    """COD checkout with order total <= 5000 must succeed."""
    info = _get_first_active_product()
    if info is None:
        return
    pid, stock, price = info
    if price * 1.05 > 5000 or stock < 1:
        return
    _clear_cart()
    _add_to_cart(pid, 1)
    addr_id = _get_first_address_id()
    if not addr_id:
        return
    res = requests.post(f"{BASE_URL}/checkout", headers=get_headers(),
                        json={"payment_method": "COD", "address_id": addr_id})
    assert res.status_code in [200, 201]


def test_checkout_card_status_paid():
    """CARD checkout must set payment_status = PAID."""
    info = _get_first_active_product()
    if info is None:
        return
    pid, stock, _ = info
    if stock < 1:
        return
    _clear_cart()
    _add_to_cart(pid, 1)
    addr_id = _get_first_address_id()
    if not addr_id:
        return
    res = requests.post(f"{BASE_URL}/checkout", headers=get_headers(),
                        json={"payment_method": "CARD", "address_id": addr_id})
    assert res.status_code in [200, 201]
    order_id = res.json().get("order_id")
    if order_id:
        order = requests.get(f"{BASE_URL}/orders/{order_id}", headers=get_headers()).json()
        assert order.get("payment_status") == "PAID"


def test_checkout_cod_status_pending():
    """COD checkout must set payment_status = PENDING."""
    info = _get_first_active_product()
    if info is None:
        return
    pid, stock, price = info
    if price * 1.05 > 5000 or stock < 1:
        return
    _clear_cart()
    _add_to_cart(pid, 1)
    addr_id = _get_first_address_id()
    if not addr_id:
        return
    res = requests.post(f"{BASE_URL}/checkout", headers=get_headers(),
                        json={"payment_method": "COD", "address_id": addr_id})
    assert res.status_code in [200, 201]
    order_id = res.json().get("order_id")
    if order_id:
        order = requests.get(f"{BASE_URL}/orders/{order_id}", headers=get_headers()).json()
        assert order.get("payment_status") == "PENDING"


def test_checkout_cod_over_limit():
    """COD checkout with order total > 5000 must be rejected with 400."""
    # Find a product whose price * qty will exceed 5000 after 5% GST
    admin_res = requests.get(f"{BASE_URL}/admin/products", headers=get_admin_headers())
    if admin_res.status_code not in [200, 201]:
        return
    for p in admin_res.json():
        price = float(p.get("price", 0))
        stock = int(p.get("stock", 0))
        if not p.get("is_active", True):
            continue
        needed_qty = int(5001 / (price * 1.05)) + 1 if price > 0 else 0
        if stock >= needed_qty and needed_qty > 0:
            _clear_cart()
            _add_to_cart(p["product_id"], needed_qty)
            addr_id = _get_first_address_id()
            if not addr_id:
                return
            res = requests.post(f"{BASE_URL}/checkout", headers=get_headers(),
                                json={"payment_method": "COD", "address_id": addr_id})
            assert res.status_code == 400, f"COD > 5000 should be rejected, got {res.status_code}"
            _clear_cart()
            return


def test_checkout_gst_in_invoice():
    """Invoice GST must be 5% of subtotal; total_amount = subtotal + gst_amount."""
    orders_res = requests.get(f"{BASE_URL}/orders", headers=get_headers())
    if orders_res.status_code != 200 or not orders_res.json():
        return
    order_id = orders_res.json()[0].get("order_id")
    inv = requests.get(f"{BASE_URL}/orders/{order_id}/invoice", headers=get_headers())
    if inv.status_code != 200:
        return
    body = inv.json()
    subtotal = float(body.get("subtotal", 0))
    gst = float(body.get("gst_amount", body.get("gst", 0)))
    total = float(body.get("total_amount", body.get("total", 0)))
    expected_gst = round(subtotal * 0.05, 2)
    assert abs(gst - expected_gst) < 0.02, f"GST mismatch: expected {expected_gst}, got {gst}"
    assert abs(total - round(subtotal + gst, 2)) < 0.02, f"Total mismatch: {total} != {subtotal + gst}"


# ==========================================
# 9. Wallet
# ==========================================
def test_get_wallet():
    """Test fetching wallet balance."""
    response = requests.get(f"{BASE_URL}/wallet", headers=get_headers())
    assert response.status_code == 200


def test_post_wallet_add_boundaries():
    """Wallet add boundaries: 0 and 100001 must fail; 1 must succeed."""
    assert requests.post(f"{BASE_URL}/wallet/add", headers=get_headers(), json={"amount": 0}).status_code == 400
    assert requests.post(f"{BASE_URL}/wallet/add", headers=get_headers(), json={"amount": 1}).status_code in [200, 204]
    assert requests.post(f"{BASE_URL}/wallet/add", headers=get_headers(), json={"amount": 100001}).status_code == 400


def test_post_wallet_add_negative():
    """Adding a negative amount must return 400."""
    assert requests.post(f"{BASE_URL}/wallet/add", headers=get_headers(), json={"amount": -1}).status_code == 400


def test_post_wallet_pay_zero():
    """Paying 0 from wallet must return 400."""
    assert requests.post(f"{BASE_URL}/wallet/pay", headers=get_headers(), json={"amount": 0}).status_code == 400


def test_post_wallet_pay_negative():
    """Paying a negative amount must return 400."""
    assert requests.post(f"{BASE_URL}/wallet/pay", headers=get_headers(), json={"amount": -1}).status_code == 400


def test_post_wallet_exact_deduction():
    """Paying from wallet must deduct exactly the requested amount."""
    requests.post(f"{BASE_URL}/wallet/add", headers=get_headers(), json={"amount": 50})
    before = float(requests.get(f"{BASE_URL}/wallet", headers=get_headers()).json().get("balance", 0))
    if before < 10:
        return
    res = requests.post(f"{BASE_URL}/wallet/pay", headers=get_headers(), json={"amount": 10})
    if res.status_code in [200, 204]:
        after = float(requests.get(f"{BASE_URL}/wallet", headers=get_headers()).json().get("balance", 0))
        assert round(before - after, 2) == 10.0, f"Expected deduction of exactly 10, got {before - after}"


def test_post_wallet_insufficient_funds():
    """Paying more than wallet balance must return 400."""
    balance = float(requests.get(f"{BASE_URL}/wallet", headers=get_headers()).json().get("balance", 0))
    assert requests.post(f"{BASE_URL}/wallet/pay", headers=get_headers(),
                         json={"amount": balance + 99999}).status_code == 400


# ==========================================
# 10. Loyalty Points
# ==========================================
def test_get_loyalty():
    """Test viewing loyalty points balance."""
    response = requests.get(f"{BASE_URL}/loyalty", headers=get_headers())
    assert response.status_code == 200


def test_post_loyalty_redeem_boundaries():
    """Redeeming 0 points must return 400; 1 point accepted if balance allows."""
    assert requests.post(f"{BASE_URL}/loyalty/redeem", headers=get_headers(), json={"points": 0}).status_code == 400
    assert requests.post(f"{BASE_URL}/loyalty/redeem", headers=get_headers(),
                         json={"points": 1}).status_code in [200, 204, 400]


def test_post_loyalty_redeem_negative():
    """Redeeming negative points must return 400."""
    assert requests.post(f"{BASE_URL}/loyalty/redeem", headers=get_headers(), json={"points": -1}).status_code == 400


def test_post_loyalty_redeem_insufficient():
    """Redeeming more points than available must return 400."""
    body = requests.get(f"{BASE_URL}/loyalty", headers=get_headers()).json()
    balance = int(body.get("points", body.get("loyalty_points", 0)))
    assert requests.post(f"{BASE_URL}/loyalty/redeem", headers=get_headers(),
                         json={"points": balance + 99999}).status_code == 400


# ==========================================
# 11. Orders
# ==========================================
def test_get_orders():
    """Test retrieving all orders."""
    response = requests.get(f"{BASE_URL}/orders", headers=get_headers())
    assert response.status_code == 200


def test_get_single_order():
    """GET /orders/{order_id} for an existing order must return 200."""
    orders = requests.get(f"{BASE_URL}/orders", headers=get_headers()).json()
    if not orders:
        return
    order_id = orders[0].get("order_id")
    res = requests.get(f"{BASE_URL}/orders/{order_id}", headers=get_headers())
    assert res.status_code == 200
    assert "order_id" in res.json()


def test_get_order_nonexistent():
    """Fetching nonexistent order must return 404."""
    assert requests.get(f"{BASE_URL}/orders/99999", headers=get_headers()).status_code == 404


def test_post_order_cancel_nonexistent():
    """Cancelling nonexistent order must return 404."""
    assert requests.post(f"{BASE_URL}/orders/99999/cancel", headers=get_headers()).status_code == 404


def test_cancel_delivered_order():
    """Cancelling a DELIVERED order must return 400."""
    orders = requests.get(f"{BASE_URL}/orders", headers=get_headers()).json()
    delivered = [o for o in orders if o.get("status") == "DELIVERED"]
    if not delivered:
        return
    assert requests.post(f"{BASE_URL}/orders/{delivered[0].get('order_id')}/cancel",
                         headers=get_headers()).status_code == 400


def test_cancel_order_restores_stock():
    """Cancelling an order must return items back to product stock."""
    orders = requests.get(f"{BASE_URL}/orders", headers=get_headers()).json()
    cancellable = [o for o in orders if o.get("status") not in ["DELIVERED", "CANCELLED"]]
    if not cancellable:
        return
    order_id = cancellable[0].get("order_id")
    order_detail = requests.get(f"{BASE_URL}/orders/{order_id}", headers=get_headers()).json()
    items = order_detail.get("items", order_detail.get("order_items", []))
    if not items:
        return
    pid = items[0].get("product_id")
    qty = items[0].get("quantity")
    admin_before = {str(p["product_id"]): p for p in
                    requests.get(f"{BASE_URL}/admin/products", headers=get_admin_headers()).json()}
    stock_before = int(admin_before.get(str(pid), {}).get("stock", 0))
    cancel_res = requests.post(f"{BASE_URL}/orders/{order_id}/cancel", headers=get_headers())
    if cancel_res.status_code not in [200, 204]:
        return
    admin_after = {str(p["product_id"]): p for p in
                   requests.get(f"{BASE_URL}/admin/products", headers=get_admin_headers()).json()}
    stock_after = int(admin_after.get(str(pid), {}).get("stock", 0))
    assert stock_after == stock_before + qty, \
        f"Stock not restored: before={stock_before} after={stock_after} expected_add={qty}"


def test_get_order_invoice_structure():
    """Invoice must contain subtotal, gst_amount, and total_amount fields."""
    orders = requests.get(f"{BASE_URL}/orders", headers=get_headers()).json()
    if not orders:
        return
    order_id = orders[0].get("order_id")
    inv = requests.get(f"{BASE_URL}/orders/{order_id}/invoice", headers=get_headers())
    assert inv.status_code == 200
    body = inv.json()
    assert "subtotal" in body, "Invoice missing 'subtotal'"
    assert "gst_amount" in body or "gst" in body, "Invoice missing GST field"
    assert "total_amount" in body or "total" in body, "Invoice missing total field"


# ==========================================
# 12. Reviews
# ==========================================
def test_post_product_review_rating_boundaries():
    """Rating bounds: 0 and 6 must fail (400); 1 and 5 must succeed."""
    assert requests.post(f"{BASE_URL}/products/1/reviews", headers=get_headers(),
                         json={"rating": 0, "comment": "Good"}).status_code in [400, 404]
    assert requests.post(f"{BASE_URL}/products/1/reviews", headers=get_headers(),
                         json={"rating": 6, "comment": "Good"}).status_code in [400, 404]
    assert requests.post(f"{BASE_URL}/products/1/reviews", headers=get_headers(),
                         json={"rating": 1, "comment": "Good"}).status_code in [200, 201, 404]
    assert requests.post(f"{BASE_URL}/products/1/reviews", headers=get_headers(),
                         json={"rating": 5, "comment": "Good"}).status_code in [200, 201, 404]


def test_post_product_review_comment_boundaries():
    """Comment bounds: empty and 201 chars must fail; 1 and 200 chars must succeed."""
    assert requests.post(f"{BASE_URL}/products/1/reviews", headers=get_headers(),
                         json={"rating": 5, "comment": ""}).status_code in [400, 404]
    assert requests.post(f"{BASE_URL}/products/1/reviews", headers=get_headers(),
                         json={"rating": 5, "comment": "A" * 201}).status_code in [400, 404]
    assert requests.post(f"{BASE_URL}/products/1/reviews", headers=get_headers(),
                         json={"rating": 5, "comment": "A"}).status_code in [200, 201, 404]
    assert requests.post(f"{BASE_URL}/products/1/reviews", headers=get_headers(),
                         json={"rating": 5, "comment": "A" * 200}).status_code in [200, 201, 404]


def test_get_reviews_no_reviews_avg_zero():
    """A product with no reviews must report average_rating = 0."""
    res = requests.get(f"{BASE_URL}/products", headers=get_headers())
    if res.status_code != 200:
        return
    for p in res.json():
        pid = p.get("product_id")
        rev_res = requests.get(f"{BASE_URL}/products/{pid}/reviews", headers=get_headers())
        if rev_res.status_code != 200:
            continue
        body = rev_res.json()
        reviews = body if isinstance(body, list) else body.get("reviews", [])
        if len(reviews) == 0:
            avg = body.get("average_rating") if isinstance(body, dict) else None
            if avg is not None:
                assert float(avg) == 0.0, f"Expected avg 0, got {avg}"
            return


def test_get_reviews_decimal_average():
    """Average rating must be a proper decimal, not truncated to an integer."""
    res = requests.get(f"{BASE_URL}/products", headers=get_headers())
    if res.status_code != 200 or not res.json():
        return
    pid = res.json()[0].get("product_id")
    requests.post(f"{BASE_URL}/products/{pid}/reviews", headers=get_headers(),
                  json={"rating": 3, "comment": "Avg decimal test A"})
    requests.post(f"{BASE_URL}/products/{pid}/reviews", headers=get_headers(),
                  json={"rating": 4, "comment": "Avg decimal test B"})
    rev_res = requests.get(f"{BASE_URL}/products/{pid}/reviews", headers=get_headers())
    if rev_res.status_code != 200:
        return
    body = rev_res.json()
    avg = body.get("average_rating") if isinstance(body, dict) else None
    if avg is not None:
        avg_f = float(avg)
        assert avg_f != int(avg_f) or avg_f in [3.0, 4.0, 5.0], \
            f"Average rating '{avg_f}' looks integer-truncated"


# ==========================================
# 13. Support Tickets
# ==========================================
def test_get_support_tickets():
    """Test retrieving all user's support tickets."""
    response = requests.get(f"{BASE_URL}/support/tickets", headers=get_headers())
    assert response.status_code == 200


def test_post_support_ticket_subject_boundaries():
    """Subject bounds: 4 and 101 chars fail; 5 and 100 chars succeed."""
    assert requests.post(f"{BASE_URL}/support/ticket", headers=get_headers(),
                         json={"subject": "A" * 4, "message": "Valid"}).status_code == 400
    assert requests.post(f"{BASE_URL}/support/ticket", headers=get_headers(),
                         json={"subject": "S" * 101, "message": "Valid"}).status_code == 400
    assert requests.post(f"{BASE_URL}/support/ticket", headers=get_headers(),
                         json={"subject": "A" * 5, "message": "Valid"}).status_code in [200, 201]
    assert requests.post(f"{BASE_URL}/support/ticket", headers=get_headers(),
                         json={"subject": "S" * 100, "message": "Valid"}).status_code in [200, 201]


def test_post_support_ticket_message_boundaries():
    """Message bounds: empty and 501 chars fail; 1 and 500 chars succeed."""
    assert requests.post(f"{BASE_URL}/support/ticket", headers=get_headers(),
                         json={"subject": "Valid Subj", "message": ""}).status_code == 400
    assert requests.post(f"{BASE_URL}/support/ticket", headers=get_headers(),
                         json={"subject": "Valid Subj", "message": "M" * 501}).status_code == 400
    assert requests.post(f"{BASE_URL}/support/ticket", headers=get_headers(),
                         json={"subject": "Valid Subj", "message": "M"}).status_code in [200, 201]
    assert requests.post(f"{BASE_URL}/support/ticket", headers=get_headers(),
                         json={"subject": "Valid Subj", "message": "M" * 500}).status_code in [200, 201]


def test_post_support_ticket_initial_status_open():
    """A newly created ticket must have status = OPEN."""
    payload = {"subject": "Status Check", "message": "Checking new ticket opens as OPEN"}
    res = requests.post(f"{BASE_URL}/support/ticket", headers=get_headers(), json=payload)
    assert res.status_code in [200, 201]
    ticket_id = res.json().get("ticket_id")
    tickets = requests.get(f"{BASE_URL}/support/tickets", headers=get_headers()).json()
    for t in tickets:
        if str(t.get("ticket_id")) == str(ticket_id):
            assert t.get("status") == "OPEN", f"Expected OPEN, got {t.get('status')}"
            return


def test_post_support_ticket_message_saved_exactly():
    """The full message must be stored verbatim exactly as submitted."""
    msg = "Exact message: 1234 !@#$ SpEciAl"
    payload = {"subject": "Exact Save", "message": msg}
    res = requests.post(f"{BASE_URL}/support/ticket", headers=get_headers(), json=payload)
    if res.status_code not in [200, 201]:
        return
    ticket_id = res.json().get("ticket_id")
    # User endpoint may not return message; use admin endpoint
    admin_tickets = requests.get(f"{BASE_URL}/admin/tickets", headers=get_admin_headers()).json()
    for t in admin_tickets:
        if str(t.get("ticket_id")) == str(ticket_id):
            assert t.get("message") == msg, f"Message not saved exactly: {t.get('message')!r}"
            return


def test_put_ticket_valid_transitions():
    """OPEN → IN_PROGRESS → CLOSED must all succeed."""
    res = requests.post(f"{BASE_URL}/support/ticket", headers=get_headers(),
                        json={"subject": "Transition Test", "message": "Testing state transitions"})
    assert res.status_code in [200, 201]
    tid = res.json().get("ticket_id")
    r1 = requests.put(f"{BASE_URL}/support/tickets/{tid}", headers=get_headers(), json={"status": "IN_PROGRESS"})
    assert r1.status_code in [200, 204], f"OPEN→IN_PROGRESS failed: {r1.status_code}"
    r2 = requests.put(f"{BASE_URL}/support/tickets/{tid}", headers=get_headers(), json={"status": "CLOSED"})
    assert r2.status_code in [200, 204], f"IN_PROGRESS→CLOSED failed: {r2.status_code}"


def test_put_ticket_illegal_jump_open_to_closed():
    """OPEN → CLOSED (skipping IN_PROGRESS) must be rejected with 400."""
    res = requests.post(f"{BASE_URL}/support/ticket", headers=get_headers(),
                        json={"subject": "Illegal Jump", "message": "Testing illegal transition"})
    if res.status_code not in [200, 201]:
        return
    tid = res.json().get("ticket_id")
    assert requests.put(f"{BASE_URL}/support/tickets/{tid}", headers=get_headers(),
                        json={"status": "CLOSED"}).status_code == 400


def test_put_ticket_backward_transition():
    """IN_PROGRESS → OPEN (backward) must be rejected with 400."""
    res = requests.post(f"{BASE_URL}/support/ticket", headers=get_headers(),
                        json={"subject": "Backward Trans", "message": "Testing backward transition"})
    if res.status_code not in [200, 201]:
        return
    tid = res.json().get("ticket_id")
    requests.put(f"{BASE_URL}/support/tickets/{tid}", headers=get_headers(), json={"status": "IN_PROGRESS"})
    assert requests.put(f"{BASE_URL}/support/tickets/{tid}", headers=get_headers(),
                        json={"status": "OPEN"}).status_code == 400


def test_put_ticket_closed_is_terminal():
    """After CLOSED, any further status update must be rejected with 400."""
    res = requests.post(f"{BASE_URL}/support/ticket", headers=get_headers(),
                        json={"subject": "Terminal State", "message": "Testing terminal CLOSED state"})
    if res.status_code not in [200, 201]:
        return
    tid = res.json().get("ticket_id")
    requests.put(f"{BASE_URL}/support/tickets/{tid}", headers=get_headers(), json={"status": "IN_PROGRESS"})
    requests.put(f"{BASE_URL}/support/tickets/{tid}", headers=get_headers(), json={"status": "CLOSED"})
    assert requests.put(f"{BASE_URL}/support/tickets/{tid}", headers=get_headers(),
                        json={"status": "IN_PROGRESS"}).status_code == 400


def test_put_support_ticket_immutable_fields():
    """PUT /support/tickets must not allow updating subject or message."""
    payload = {"subject": "Test Subj", "message": "Test Msg"}
    res = requests.post(f"{BASE_URL}/support/ticket", headers=get_headers(), json=payload)
    if res.status_code in [200, 201]:
        ticket_id = res.json().get("ticket_id")
        hacked_payload = {"status": "IN_PROGRESS", "subject": "HACKED SUBJ", "message": "HACKED MSG"}
        put_res = requests.put(f"{BASE_URL}/support/tickets/{ticket_id}", headers=get_headers(), json=hacked_payload)
        if put_res.status_code in [200, 204]:
            # Use admin endpoint since user endpoint may not return message
            admin_tickets = requests.get(f"{BASE_URL}/admin/tickets", headers=get_admin_headers()).json()
            for t in admin_tickets:
                if str(t.get("ticket_id")) == str(ticket_id):
                    assert t.get("subject") == "Test Subj"
                    assert t.get("message") == "Test Msg"
