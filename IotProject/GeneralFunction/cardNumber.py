"""Membership card numbers: 11 digits = 10 random digits + 1 check digit (Luhn).
The check digit catches typos and made-up numbers without touching the database."""
import secrets

CARD_LENGTH = 11


def luhnCheckDigit(payload):
    total = 0
    for position, char in enumerate(reversed(payload)):
        digit = int(char)
        if position % 2 == 0:          # every second digit, starting next to the check digit
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return str((10 - total % 10) % 10)


def isValidCardNumber(value):
    return (isinstance(value, str) and len(value) == CARD_LENGTH and value.isdigit()
            and luhnCheckDigit(value[:-1]) == value[-1])


def newCardNumber():
    """A random card number. The caller must still check it is not already taken."""
    body = str(secrets.randbelow(9) + 1) + "".join(str(secrets.randbelow(10)) for _ in range(CARD_LENGTH - 2))
    return body + luhnCheckDigit(body)