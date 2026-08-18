export interface PasswordValidation {
  minLength: boolean;
  hasUppercase: boolean;
  hasLowercase: boolean;
  hasDigit: boolean;
  hasSpecial: boolean;
}

const SPECIAL_CHARS = /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?~`]/;

function hasAsciiDigit(password: string): boolean {
  for (const ch of password) {
    if (ch >= "0" && ch <= "9") {
      return true;
    }
  }
  return false;
}

export function validatePassword(password: string): PasswordValidation {
  return {
    minLength: password.length >= 8,
    hasUppercase: /[A-Z]/.test(password),
    hasLowercase: /[a-z]/.test(password),
    hasDigit: hasAsciiDigit(password),
    hasSpecial: SPECIAL_CHARS.test(password),
  };
}

export function isPasswordValid(validation: PasswordValidation): boolean {
  return (
    validation.minLength &&
    validation.hasUppercase &&
    validation.hasLowercase &&
    validation.hasDigit &&
    validation.hasSpecial
  );
}
