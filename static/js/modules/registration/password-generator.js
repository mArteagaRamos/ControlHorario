/**
 * password-generator.js
 * Temporary password generation utility
 *
 * Functions:
 * - generatePassword(length)
 */

/**
 * Generate a secure temporary password
 * Contains: uppercase, lowercase, digits, special chars
 *
 * @param {number} length - Password length (default: 12)
 * @returns {string} Generated password
 */
export function generatePassword(length = 12) {
  const upper  = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  const lower  = 'abcdefghijklmnopqrstuvwxyz';
  const digits = '0123456789';
  const special = '!@#$%&*?';
  const all = upper + lower + digits + special;

  // Ensure at least one of each character type
  let password = [
    upper[Math.floor(Math.random() * upper.length)],
    lower[Math.floor(Math.random() * lower.length)],
    digits[Math.floor(Math.random() * digits.length)],
    special[Math.floor(Math.random() * special.length)],
  ];

  // Fill remaining length with random chars
  for (let i = 4; i < length; i++) {
    password.push(all[Math.floor(Math.random() * all.length)]);
  }

  // Shuffle the array
  return password.sort(() => Math.random() - 0.5).join('');
}
