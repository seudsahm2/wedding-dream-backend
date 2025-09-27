import hashlib
import re
from typing import Tuple


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def normalize_user_agent(ua: str | None) -> str:
    if not ua:
        return ''
    return ua.strip()[:300]


def derive_label(ua: str) -> str:
    if not ua:
        return 'Unknown Device'
    ua_lower = ua.lower()
    # Simple heuristics (avoid extra dependency)
    if 'iphone' in ua_lower:
        return 'iPhone'
    if 'ipad' in ua_lower:
        return 'iPad'
    if 'android' in ua_lower and 'mobile' in ua_lower:
        return 'Android Phone'
    if 'android' in ua_lower:
        return 'Android Device'
    if 'mac os x' in ua_lower or 'macintosh' in ua_lower:
        return 'Mac'
    if re.search(r'windows nt 1?0|windows nt 6', ua_lower):
        return 'Windows PC'
    if 'linux' in ua_lower:
        return 'Linux'
    return 'Device'


def hash_ip(ip: str | None, salt: str) -> str:
    if not ip:
        return ''
    return sha256_hex(f"{salt}:{ip}")


def session_hashes(jti: str, ua: str | None, ip: str | None, ip_salt: str) -> Tuple[str, str, str, str]:
    norm_ua = normalize_user_agent(ua)
    jti_hash = sha256_hex(jti)
    ua_hash = sha256_hex(norm_ua) if norm_ua else ''
    ip_hash = hash_ip(ip, ip_salt)
    label = derive_label(norm_ua)
    return jti_hash, ua_hash, ip_hash, label
