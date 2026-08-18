"""Authentication service layer.

Handles user registration, password hashing (bcrypt 12 rounds),
password policy validation, credential verification, JWT token management,
and session storage in Redis.
"""

import re
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.exceptions import AuthenticationError, ValidationError
from app.models.user import User
from app.schemas.auth import RegisterRequest

# Number of bcrypt salt rounds (requirement 9.2)
_BCRYPT_ROUNDS = 12

# JWT algorithm (requirement 9.1)
_JWT_ALGORITHM = "HS256"


class AuthService:
    """Service class for authentication-related operations."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt with 12 salt rounds.

        Args:
            password: Plain-text password to hash.

        Returns:
            The bcrypt hash string.
        """
        salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """Verify a plain-text password against a bcrypt hash.

        Args:
            plain: Plain-text password to verify.
            hashed: The stored bcrypt hash.

        Returns:
            True if the password matches, False otherwise.
        """
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_password_policy(password: str) -> list[str]:
        """Validate password against the security policy.

        Policy (requirement 9.8):
        - Minimum 8 characters
        - At least 1 uppercase letter
        - At least 1 lowercase letter
        - At least 1 digit
        - At least 1 special character

        Args:
            password: The password to validate.

        Returns:
            List of Thai-language violation messages. Empty list if valid.
        """
        violations: list[str] = []

        if len(password) < 8:
            violations.append("รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร")

        if not re.search(r"[A-Z]", password):
            violations.append("รหัสผ่านต้องมีตัวอักษรพิมพ์ใหญ่อย่างน้อย 1 ตัว")

        if not re.search(r"[a-z]", password):
            violations.append("รหัสผ่านต้องมีตัวอักษรพิมพ์เล็กอย่างน้อย 1 ตัว")

        if not re.search(r"\d", password):
            violations.append("รหัสผ่านต้องมีตัวเลขอย่างน้อย 1 ตัว")

        if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;':\",./<>?\\`~]", password):
            violations.append("รหัสผ่านต้องมีอักขระพิเศษอย่างน้อย 1 ตัว")

        return violations

    @staticmethod
    async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
        """Register a new user.

        Validates password policy, checks email uniqueness, hashes password,
        and creates the user record.

        Args:
            db: Async database session.
            data: Registration request data.

        Returns:
            The created User ORM instance.

        Raises:
            ValidationError: If password policy is violated or email already exists.
        """
        # Validate password policy
        violations = AuthService.validate_password_policy(data.password)
        if violations:
            raise ValidationError(
                message=violations[0],
                field="password",
                details=violations,
            )

        # Check email uniqueness
        stmt = select(User).where(User.email == data.email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        if existing_user is not None:
            raise ValidationError(
                message="อีเมลนี้ถูกใช้งานแล้ว",
                field="email",
            )

        # Hash password and create user
        password_hash = AuthService.hash_password(data.password)
        user = User(
            name=data.name,
            email=data.email,
            password_hash=password_hash,
            organization=data.organization,
            role=data.role,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

        return user

    @staticmethod
    def create_token(user_id: str, role: str) -> str:
        """Create a JWT token with HS256 signing.

        The token includes:
        - sub: user_id
        - role: user role
        - jti: unique token identifier (for session tracking)
        - exp: expiration time (now + jwt_expiry_hours)
        - iat: issued at time

        Args:
            user_id: The user's UUID as string.
            role: The user's role.

        Returns:
            The encoded JWT token string.
        """
        settings = get_settings()
        now = datetime.now(timezone.utc)
        jti = str(uuid.uuid4())

        payload = {
            "sub": user_id,
            "role": role,
            "jti": jti,
            "iat": now,
            "exp": now + timedelta(hours=settings.jwt_expiry_hours),
        }

        token = jwt.encode(payload, settings.jwt_secret, algorithm=_JWT_ALGORITHM)
        return token

    @staticmethod
    def decode_token(token: str) -> dict:
        """Decode and validate a JWT token.

        Args:
            token: The JWT token string to decode.

        Returns:
            The decoded payload dictionary with keys: sub, role, jti, iat, exp.

        Raises:
            AuthenticationError: If the token is invalid, expired, or malformed.
        """
        settings = get_settings()
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[_JWT_ALGORITHM],
            )
            return payload
        except ExpiredSignatureError:
            raise AuthenticationError(
                message="โทเค็นหมดอายุ กรุณาเข้าสู่ระบบใหม่",
            )
        except JWTError:
            raise AuthenticationError(
                message="โทเค็นไม่ถูกต้อง",
            )

    @staticmethod
    async def login(db: AsyncSession, redis, email: str, password: str) -> tuple[User, str]:
        """Authenticate user and create session.

        Verifies credentials, generates a JWT token, and stores the session
        in Redis with key `session:{user_id}:{jti}` and TTL = jwt_expiry_hours.

        Args:
            db: Async database session.
            redis: Redis client instance.
            email: User email address.
            password: Plain-text password.

        Returns:
            Tuple of (User instance, JWT token string).

        Raises:
            AuthenticationError: If credentials are invalid.
        """
        settings = get_settings()

        # Fetch user by email
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            raise AuthenticationError(
                message="อีเมลหรือรหัสผ่านไม่ถูกต้อง",
            )

        # Verify password
        if not AuthService.verify_password(password, user.password_hash):
            raise AuthenticationError(
                message="อีเมลหรือรหัสผ่านไม่ถูกต้อง",
            )

        # Create JWT token
        token = AuthService.create_token(str(user.id), user.role)

        # Store session in Redis
        payload = AuthService.decode_token(token)
        jti = payload["jti"]
        session_key = f"session:{user.id}:{jti}"
        ttl_seconds = settings.jwt_expiry_hours * 3600

        if redis is not None:
            await redis.set(session_key, "active", ex=ttl_seconds)

        return user, token

    @staticmethod
    async def logout(redis, token: str) -> None:
        """Invalidate a session by removing it from Redis.

        Args:
            redis: Redis client instance.
            token: The JWT token to invalidate.

        Raises:
            AuthenticationError: If the token is invalid.
        """
        payload = AuthService.decode_token(token)
        user_id = payload["sub"]
        jti = payload["jti"]
        session_key = f"session:{user_id}:{jti}"

        if redis is not None:
            await redis.delete(session_key)
