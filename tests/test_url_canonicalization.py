import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from backend.api_routes import canonicalize_url, is_valid_domain

def test_valid_domains():
    assert is_valid_domain("https://amazon.in/dp/B08N5WRWNW") is True
    assert is_valid_domain("https://www.amazon.in/dp/B08N5WRWNW") is True
    assert is_valid_domain("https://amzn.in/d/079gH9Y1") is True
    assert is_valid_domain("https://flipkart.com/p/itm123?pid=MOB123") is True
    assert is_valid_domain("https://www.flipkart.com/p/itm123?pid=MOB123") is True
    assert is_valid_domain("https://dl.flipkart.com/s/sample") is True

def test_invalid_and_malformed_domains():
    assert is_valid_domain("https://google.com") is False
    assert is_valid_domain("https://myfakeshop.com/amazon.in") is False
    assert is_valid_domain("not-a-url") is False
    assert is_valid_domain("") is False

def test_canonicalize_amazon_standard_url():
    url = "https://www.amazon.in/dp/B08N5WRWNW?ref=sr_1_1"
    res = canonicalize_url(url)
    assert res["platform"] == "amazon"
    assert res["pid"] == "B08N5WRWNW"
    assert res["canonical_url"] == "https://www.amazon.in/dp/B08N5WRWNW"

def test_canonicalize_amazon_bare_domain():
    url = "https://amazon.in/dp/B08N5WRWNW"
    res = canonicalize_url(url)
    assert res["platform"] == "amazon"
    assert res["pid"] == "B08N5WRWNW"
    assert res["canonical_url"] == "https://www.amazon.in/dp/B08N5WRWNW"

def test_canonicalize_amzn_in_short_url():
    url = "https://amzn.in/d/079gH9Y1"
    res = canonicalize_url(url)
    assert res["platform"] == "amazon"
    assert res["canonical_url"] == "https://amzn.in/d/079gH9Y1"

def test_canonicalize_flipkart_standard_url():
    url = "https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac2b85e2676b?pid=MOBGTAGPTTVZ2THW"
    res = canonicalize_url(url)
    assert res["platform"] == "flipkart"
    assert res["pid"] == "MOBGTAGPTTVZ2THW"
    assert res["canonical_url"] == "https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac2b85e2676b?pid=MOBGTAGPTTVZ2THW"

def test_canonicalize_flipkart_bare_domain():
    url = "https://flipkart.com/p/itm6ac2b85e2676b?pid=MOBGTAGPTTVZ2THW"
    res = canonicalize_url(url)
    assert res["platform"] == "flipkart"
    assert res["pid"] == "MOBGTAGPTTVZ2THW"
    assert res["canonical_url"] == "https://www.flipkart.com/p/itm6ac2b85e2676b?pid=MOBGTAGPTTVZ2THW"

def test_canonicalize_invalid_domain_raises_value_error():
    with pytest.raises(ValueError, match="Only official Amazon India and Flipkart URLs are supported"):
        canonicalize_url("https://ebay.com/item/123")

def test_canonicalize_malformed_url_raises_value_error():
    with pytest.raises(ValueError):
        canonicalize_url("just_random_text_123")
