"""Unit tests for AuthService.

Tests password hashing, verification, and password policy validation.
"""

import pytest

from app.services.auth_service import AuthService


class TestHashPassword:
    """Tests for AuthService.hash_password."""

    def test_returns_bcrypt_hash(self):
        """hash_password returns a bcrypt-prefixed hash string."""
        result = AuthService.hash_password("TestPassword1!")
        assert result.startswith("$2b$") or result.startswith("$2a$")

    def test_hash_contains_12_rounds(self):
        """hash_password uses 12 salt rounds as per requirement 9.2."""
        result = AuthService.hash_password("TestPassword1!")
        # bcrypt hash format: $2b$12$...
        parts = result.split("$")
        assert parts[2] == "12"

    def test_different_passwords_produce_different_hashes(self):
        """Different passwords should produce different hashes."""
        h1 = AuthService.hash_password("Password1!")
        h2 = AuthService.hash_password("Password2!")
        assert h1 != h2

    def test_same_password_produces_different_hashes(self):
        """Same password hashed twice should differ due to random salt."""
        h1 = AuthService.hash_password("SamePassword1!")
        h2 = AuthService.hash_password("SamePassword1!")
        assert h1 != h2


class TestVerifyPassword:
    """Tests for AuthService.verify_password."""

    def test_correct_password_returns_true(self):
        """verify_password returns True for the correct plain text."""
        hashed = AuthService.hash_password("MySecret@123")
        assert AuthService.verify_password("MySecret@123", hashed) is True

    def test_wrong_password_returns_false(self):
        """verify_password returns False for incorrect password."""
        hashed = AuthService.hash_password("MySecret@123")
        assert AuthService.verify_password("WrongPass@123", hashed) is False

    def test_empty_password_returns_false(self):
        """verify_password returns False for empty string."""
        hashed = AuthService.hash_password("MySecret@123")
        assert AuthService.verify_password("", hashed) is False


class TestValidatePasswordPolicy:
    """Tests for AuthService.validate_password_policy."""

    def test_valid_password_returns_empty_list(self):
        """A valid password that meets all criteria returns no violations."""
        violations = AuthService.validate_password_policy("Str0ng@Pass")
        assert violations == []

    def test_too_short(self):
        """Password shorter than 8 characters is flagged."""
        violations = AuthService.validate_password_policy("Ab1!")
        assert "รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร" in violations

    def test_no_uppercase(self):
        """Password without uppercase letter is flagged."""
        violations = AuthService.validate_password_policy("password1!")
        assert "รหัสผ่านต้องมีตัวอักษรพิมพ์ใหญ่อย่างน้อย 1 ตัว" in violations

    def test_no_lowercase(self):
        """Password without lowercase letter is flagged."""
        violations = AuthService.validate_password_policy("PASSWORD1!")
        assert "รหัสผ่านต้องมีตัวอักษรพิมพ์เล็กอย่างน้อย 1 ตัว" in violations

    def test_no_digit(self):
        """Password without digit is flagged."""
        violations = AuthService.validate_password_policy("Password!")
        assert "รหัสผ่านต้องมีตัวเลขอย่างน้อย 1 ตัว" in violations

    def test_no_special_char(self):
        """Password without special character is flagged."""
        violations = AuthService.validate_password_policy("Password1a")
        assert "รหัสผ่านต้องมีอักขระพิเศษอย่างน้อย 1 ตัว" in violations

    def test_multiple_violations(self):
        """Password that fails multiple criteria returns all violations."""
        violations = AuthService.validate_password_policy("abc")
        # Should at least have: too short, no uppercase, no digit, no special
        assert len(violations) >= 3

    def test_exactly_8_chars_is_valid_length(self):
        """Password with exactly 8 characters passes length check."""
        violations = AuthService.validate_password_policy("Abcde1!x")
        assert "รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร" not in violations

    def test_special_chars_variety(self):
        """Various special characters are accepted."""
        for char in ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")"]:
            password = f"Abcdef1{char}"
            violations = AuthService.validate_password_policy(password)
            assert "รหัสผ่านต้องมีอักขระพิเศษอย่างน้อย 1 ตัว" not in violations
