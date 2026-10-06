"""Feature extraction for CatchPhish Tier 1 and Tier 2 scoring."""
import re
import os
import json
import ipaddress
import unicodedata
from difflib import SequenceMatcher
from urllib.parse import urlparse

TRUSTED_DOMAINS = {
    "google.com", "youtube.com", "github.com", "gitlab.com", "microsoft.com",
    "apple.com", "amazon.com", "wikipedia.org", "twitter.com", "x.com",
    "facebook.com", "instagram.com", "linkedin.com", "reddit.com", "netflix.com",
    "stackoverflow.com", "pypi.org", "npmjs.com", "python.org", "mozilla.org",
    "wordpress.com", "adobe.com", "salesforce.com", "oracle.com", "ibm.com",
    "cloudflare.com", "openai.com", "anthropic.com", "paypal.com", "nytimes.com",
    "bbc.com", "cnn.com", "who.int", "un.org", "gov.in", "nic.in", "cit.edu.in",
}

CONFUSABLES = str.maketrans({
    "а": "a", "Α": "a", "А": "a", "с": "c", "С": "c", "е": "e", "Е": "e",
    "і": "i", "І": "i", "ј": "j", "Ј": "j", "о": "o", "О": "o", "р": "p",
    "Р": "p", "у": "y", "У": "y", "х": "x", "Х": "x", "ν": "v", "Ν": "v",
    "ο": "o", "Ο": "o", "ρ": "p", "Ρ": "p",
})
COMMON_TLDS = {
    "com", "org", "net", "edu", "gov", "io", "co", "ai", "app", "dev", "me",
    "info", "biz", "in", "uk", "us", "ca", "au", "de", "fr", "jp", "cn",
    "xyz", "online", "site", "tech",
}

_LOOKUP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "tld_lookup.json")
with open(_LOOKUP_PATH) as f:
    _tld_data = json.load(f)
TLD_LOOKUP = _tld_data["lookup"]
DEFAULT_TLD_PROB = _tld_data["default"]

LEXICAL_HOST_FEATURES = [
    'URLLength', 'DomainLength', 'IsDomainIP', 'TLDLength', 'TLDLegitimateProb',
    'HasObfuscation', 'NoOfObfuscatedChar', 'ObfuscationRatio', 'NoOfLettersInURL',
    'LetterRatioInURL', 'NoOfDegitsInURL', 'DegitRatioInURL', 'NoOfEqualsInURL',
    'NoOfQMarkInURL', 'NoOfAmpersandInURL', 'NoOfOtherSpecialCharsInURL',
    'SpacialCharRatioInURL', 'IsHTTPS'
]
CONTENT_FEATURES = [
    'LineOfCode', 'LargestLineLength', 'HasTitle', 'DomainTitleMatchScore',
    'URLTitleMatchScore', 'HasFavicon', 'Robots', 'IsResponsive', 'NoOfURLRedirect',
    'NoOfSelfRedirect', 'HasDescription', 'NoOfPopup', 'NoOfiFrame',
    'HasExternalFormSubmit', 'HasSocialNet', 'HasSubmitButton', 'HasHiddenFields',
    'HasPasswordField', 'Bank', 'Pay', 'Crypto', 'HasCopyrightInfo', 'NoOfImage',
    'NoOfCSS', 'NoOfJS', 'NoOfSelfRef', 'NoOfEmptyRef', 'NoOfExternalRef'
]


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def is_trusted_domain(domain: str) -> bool:
    parts = domain.lower().rstrip('.').split('.')
    for i in range(len(parts) - 1):
        if '.'.join(parts[i:]) in TRUSTED_DOMAINS:
            return True
    return False


def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, 1):
        current = [i]
        for j, char_b in enumerate(b, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (char_a != char_b)))
        previous = current
    return previous[-1]


def _comparison_domain(domain: str) -> str:
    labels = []
    for label in domain.rstrip('.').split('.'):
        try:
            decoded = label.encode('ascii').decode('idna')
        except UnicodeError:
            decoded = label
        labels.append(unicodedata.normalize('NFKC', decoded).casefold().translate(CONFUSABLES))
    return '.'.join(labels)


def lookalike_check(domain: str) -> dict:
    exact = domain.lower().rstrip('.')
    normalized = _comparison_domain(domain)
    if exact in TRUSTED_DOMAINS:
        return {'flagged': False, 'tier': None, 'matched_domain': None, 'normalized_domain': normalized,
                'edit_distance': None, 'is_punycode': False, 'reason': None}
    best_domain, best_distance = None, None
    for trusted in TRUSTED_DOMAINS:
        distance = _levenshtein(normalized, _comparison_domain(trusted))
        if best_distance is None or distance < best_distance:
            best_domain, best_distance = trusted, distance
    similarity = SequenceMatcher(None, normalized, _comparison_domain(best_domain)).ratio()
    punycode = any(label.startswith('xn--') for label in exact.split('.'))
    collision = normalized == _comparison_domain(best_domain) and exact != best_domain
    close_mutation = best_distance <= 1 or (best_distance <= 2 and similarity >= .88)
    flagged = bool(collision or close_mutation or (punycode and similarity >= .82))
    if not flagged:
        return {'flagged': False, 'tier': None, 'matched_domain': None, 'normalized_domain': normalized,
                'edit_distance': best_distance, 'is_punycode': punycode, 'reason': None}
    tier = 'Dangerous' if collision or punycode or best_distance <= 1 else 'Suspicious'
    return {'flagged': True, 'tier': tier, 'matched_domain': best_domain, 'normalized_domain': normalized,
            'edit_distance': best_distance, 'is_punycode': punycode,
            'reason': f'the domain resembles trusted {best_domain} after Unicode normalization'}


def heuristic_url_reasons(features: dict, domain: str, scheme: str) -> list[dict]:
    reasons = []
    tld = domain.rstrip('.').split('.')[-1].lower() if domain else ''
    if features.get('DomainLength', 0) >= 35:
        reasons.append({'code': 'long_domain', 'text': 'the domain is unusually long', 'direction': 'raises risk'})
    if tld and tld not in COMMON_TLDS:
        reasons.append({'code': 'uncommon_tld', 'text': f'the top-level domain .{tld} is uncommon', 'direction': 'raises risk'})
    if scheme != 'https':
        reasons.append({'code': 'no_https', 'text': 'the URL does not use HTTPS', 'direction': 'raises risk'})
    return reasons


def extract_lexical_host_features(url: str) -> dict:
    parsed = urlparse(url if '://' in url else f'http://{url}')
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.split('@')[-1]
    domain = netloc.split(':')[0]
    full_url = url
    labels = domain.split('.') if domain else []
    tld = labels[-1].lower() if len(labels) >= 2 else ''
    letters = sum(c.isalpha() for c in full_url)
    digits = sum(c.isdigit() for c in full_url)
    n_equals, n_qmark, n_amp, n_percent = (full_url.count(x) for x in ('=', '?', '&', '%'))
    other_special = sum(1 for c in full_url if not c.isalnum() and c not in '.-_/:?&=%')
    obfuscation = 1 if n_percent > 0 or '@' in full_url or _is_ip(domain) else 0
    length = len(full_url)
    return {
        'URLLength': length, 'DomainLength': len(domain), 'IsDomainIP': int(_is_ip(domain)),
        'TLDLength': len(tld), 'TLDLegitimateProb': TLD_LOOKUP.get(tld, DEFAULT_TLD_PROB),
        'HasObfuscation': obfuscation, 'NoOfObfuscatedChar': n_percent,
        'ObfuscationRatio': round(n_percent / length, 4) if length else 0,
        'NoOfLettersInURL': letters, 'LetterRatioInURL': round(letters / length, 4) if length else 0,
        'NoOfDegitInURL': digits, 'NoOfDegitsInURL': digits,
        'DegitRatioInURL': round(digits / length, 4) if length else 0,
        'NoOfEqualsInURL': n_equals, 'NoOfQMarkInURL': n_qmark, 'NoOfAmpersandInURL': n_amp,
        'NoOfOtherSpecialCharsInURL': other_special,
        'SpacialCharRatioInURL': round(other_special / length, 4) if length else 0,
        'IsHTTPS': int(scheme == 'https'),
    }, domain, scheme


def extract_content_features(url: str, timeout: float = 10.0) -> tuple[dict, dict]:
    import requests
    from bs4 import BeautifulSoup
    meta = {'error': None, 'title': None, 'final_url': url}
    defaults = {k: 0 for k in CONTENT_FEATURES}
    try:
        resp = requests.get(url if '://' in url else f'http://{url}', timeout=timeout,
                            headers={'User-Agent': 'Mozilla/5.0 (CatchPhish-Scanner/1.0)'}, allow_redirects=True)
        meta['final_url'] = resp.url
        html, soup = resp.text, BeautifulSoup(resp.text, 'html.parser')
        lines = html.splitlines()
        title = soup.title.get_text(strip=True) if soup.title else ''
        meta['title'] = title
        domain = urlparse(resp.url).netloc.split(':')[0]
        domain_title = round(SequenceMatcher(None, domain.lower(), title.lower()).ratio(), 4)
        url_title = round(SequenceMatcher(None, url.lower(), title.lower()).ratio(), 4)
        forms = soup.find_all('form')
        ext_form = int(any(f.get('action', '').startswith('http') and domain not in f.get('action', '') for f in forms))
        self_ref = empty_ref = ext_ref = has_social = 0
        social = ('facebook.com', 'twitter.com', 'x.com', 'instagram.com', 'linkedin.com', 'youtube.com', 't.me', 'whatsapp.com')
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            if href in ('', '#') or href.startswith('javascript:'):
                empty_ref += 1
            elif href.startswith('http') and domain not in href:
                ext_ref += 1
                has_social |= int(any(sd in href for sd in social))
            else:
                self_ref += 1
        text = soup.get_text(' ', strip=True).lower()
        try:
            robots = int(requests.get(f'{urlparse(resp.url).scheme}://{domain}/robots.txt',timeout=5,headers={'User-Agent': 'Mozilla/5.0 (CatchPhish-Scanner/1.0)'}).status_code == 200)
        except Exception:
            robots = 0
        return {
            'LineOfCode': len(lines), 'LargestLineLength': max((len(x) for x in lines), default=0),
            'HasTitle': int(bool(title)), 'DomainTitleMatchScore': domain_title, 'URLTitleMatchScore': url_title,
            'HasFavicon': int(bool(soup.find('link', rel=lambda v: v and 'icon' in v.lower()))),
            'Robots': robots, 'IsResponsive': int(bool(soup.find('meta', attrs={'name': 'viewport'}))),
            'NoOfURLRedirect': len(resp.history), 'NoOfSelfRedirect': sum(domain in h.url for h in resp.history),
            'HasDescription': int(bool(soup.find('meta', attrs={'name': 'description'}))),
            'NoOfPopup': html.lower().count('window.open('), 'NoOfiFrame': len(soup.find_all('iframe')),
            'HasExternalFormSubmit': ext_form, 'HasSocialNet': has_social,
            'HasSubmitButton': int(bool(soup.find('input', {'type': 'submit'}) or soup.find('button', {'type': 'submit'}))),
            'HasHiddenFields': int(bool(soup.find('input', {'type': 'hidden'}))),
            'HasPasswordField': int(bool(soup.find('input', {'type': 'password'}))),
            'Bank': int('bank' in text), 'Pay': int('pay' in text or 'payment' in text),
            'Crypto': int(any(x in text for x in ('crypto', 'bitcoin', 'wallet'))),
            'HasCopyrightInfo': int('©' in html or 'copyright' in text), 'NoOfImage': len(soup.find_all('img')),
            'NoOfCSS': len(soup.find_all('link', rel='stylesheet')) + len(soup.find_all('style')),
            'NoOfJS': len(soup.find_all('script')), 'NoOfSelfRef': self_ref, 'NoOfEmptyRef': empty_ref,
            'NoOfExternalRef': ext_ref,
        }, meta
    except Exception as e:
        meta['error'] = str(e)
        return defaults, meta
