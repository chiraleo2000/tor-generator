"""Pydantic schemas for authentication endpoints.

Defines request/response models for user registration, login, and user profile.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request body for POST /auth/register."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Full name of the user",
        examples=["สมชาย ใจดี"],
    )
    email: EmailStr = Field(
        ...,
        description="Email address (must be unique)",
        examples=["somchai@example.go.th"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 chars, 1 upper, 1 lower, 1 digit, 1 special)",
        examples=["SecureP@ss1"],
    )
    organization: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Organization or ministry name",
        examples=["กระทรวงการพัฒนาสังคมและความมั่นคงของมนุษย์"],
    )
    role: Literal["officer", "reviewer", "admin"] = Field(
        default="officer",
        description="User role (defaults to officer)",
    )


_EMAIL_ADDRESS_DESC = "Email address"


class RegisterResponse(BaseModel):
    """Response body for successful registration."""

    id: uuid.UUID = Field(..., description="Unique user ID")
    name: str = Field(..., description="Full name")
    email: str = Field(..., description=_EMAIL_ADDRESS_DESC)
    organization: str = Field(..., description="Organization name")
    role: str = Field(..., description="Assigned role")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    """Request body for POST /auth/login."""

    email: EmailStr = Field(
        ...,
        description=_EMAIL_ADDRESS_DESC,
        examples=["somchai@example.go.th"],
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="User password",
        examples=["SecureP@ss1"],
    )


class UserResponse(BaseModel):
    """User profile response (used in login response and GET /auth/me)."""

    id: uuid.UUID = Field(..., description="Unique user ID")
    name: str = Field(..., description="Full name")
    email: str = Field(..., description=_EMAIL_ADDRESS_DESC)
    organization: str = Field(..., description="Organization name")
    role: str = Field(..., description="Assigned role")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    """Response body for successful login."""

    token: str = Field(..., description="JWT access token")
    user: UserResponse = Field(..., description="Authenticated user profile")
    expires_in: int = Field(..., description="Token expiry duration in seconds")
