from app.core.config import settings


def decode_model_name(words: list) -> str:
    chars = []
    for word in words:
        low_byte = word & 0xFF
        high_byte = (word >> 8) & 0xFF
        if low_byte != 0:
            chars.append(chr(low_byte))
        if high_byte != 0:
            chars.append(chr(high_byte))
    return "".join(chars).strip()


def encode_model_name(name: str, size: int = settings.MODEL_NAME_WORDS) -> list:
    max_chars = size * 2
    padded = name.ljust(max_chars, "\x00")
    words = []
    for i in range(0, max_chars, 2):
        low_byte = ord(padded[i])
        high_byte = ord(padded[i + 1])
        words.append((high_byte << 8) | low_byte)
    return words
