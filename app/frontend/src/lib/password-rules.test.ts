import { describe, expect, it } from "vitest";
import { isPasswordValid, validatePassword } from "./password-rules";

describe("validatePassword", () => {
  it("accepts the demo seed password", () => {
    const result = validatePassword("Passw0rd!");
    expect(result).toEqual({
      minLength: true,
      hasUppercase: true,
      hasLowercase: true,
      hasDigit: true,
      hasSpecial: true,
    });
    expect(isPasswordValid(result)).toBe(true);
  });

  it("rejects a password that is missing a digit or special character", () => {
    expect(isPasswordValid(validatePassword("Password"))).toBe(false);
    expect(validatePassword("Password").hasDigit).toBe(false);
    expect(validatePassword("Password").hasSpecial).toBe(false);
  });

  it("counts ASCII digits only, not Thai digits", () => {
    expect(validatePassword("").minLength).toBe(false);
    expect(validatePassword("Abcdefg1!").hasDigit).toBe(true);
    expect(validatePassword("Password๑!").hasDigit).toBe(false);
  });
});
