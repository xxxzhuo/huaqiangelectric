from crawler.parsers.product_parser import parse_product_html
from crawler.pipelines.diff import detect_change


HTML_V1 = """
<html>
  <h1>TPS7A20</h1>
  <div class='brand'>TI</div>
  <div class='model'>TPS7A20DBVR</div>
  <div class='seller-name'>DemoShop</div>
  <div>库存: 88</div>
</html>
"""

HTML_V2 = """
<html>
  <h1>TPS7A20</h1>
  <div class='brand'>TI</div>
  <div class='model'>TPS7A20DBVR</div>
  <div class='seller-name'>DemoShop</div>
  <div>库存: 99</div>
</html>
"""


def test_parse_product_html() -> None:
    record = parse_product_html("https://s.hqew.com/product/TPS7A20DBVR", HTML_V1)
    assert record.title == "TPS7A20"
    assert record.brand == "TI"
    assert record.stock == 88


def test_detect_change_update() -> None:
    old = parse_product_html("https://s.hqew.com/product/TPS7A20DBVR", HTML_V1)
    new = parse_product_html("https://s.hqew.com/product/TPS7A20DBVR", HTML_V2)

    change = detect_change(previous=old, current=new)
    assert change.change_type == "update"
    assert "stock" in change.changed_fields
