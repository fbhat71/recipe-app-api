"""Sample tests"""
from django.test import SimpleTestCase  # type: ignore
from app import calc


class CalcTests(SimpleTestCase):
    """Tests the Calc module."""

    def test_add_numbers(self):
        """Adding numbers together"""
        res = calc.add(5, 6)
        self.assertEqual(res, 11)

    def test_subtract_numbers(self):
        """Subtracting numbers"""
        res = calc.subtract(10, 15)
        self.assertEqual(res, 5)
