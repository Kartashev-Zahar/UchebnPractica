import re


PHONE_PATTERN = re.compile(r"^(?:\+7|8)\s?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}$")


def normalize_phone(value):
    value = value.strip()
    if not PHONE_PATTERN.fullmatch(value):
        return ""
    digits = re.sub(r"\D", "", value)
    if digits.startswith("8"):
        digits = digits[1:]
    elif digits.startswith("7"):
        digits = digits[1:]
    return f"+7{digits}"
