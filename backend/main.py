"""CatchPhish FastAPI backend."""
import os, json, time, uuid
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from feature_extraction import extract_lexical_host_features, extract_content_features, is_trusted_domain, lookalike_check, heuristic_url_reasons
import risk_engine
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), 'frontend')
HISTORY_FILE = os.path.join(BASE_DIR, 'scan_history.json')
app = FastAPI(title='CatchPhish API')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

class ScanRequest(BaseModel):
    url: str
    mode: str = 'fast'

def _load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f: return json.load(f)
    return []

def _save_history(history):
    with open(HISTORY_FILE, 'w') as f: json.dump(history[-50:], f, indent=2)

def _record(result):
    history = _load_history(); history.append({'id': result['id'], 'url': result['url'], 'tier': result['final_tier'],
        'risk_score': result['final_risk_score'], 'escalated': result['escalated'], 'timestamp': result['timestamp']}); _save_history(history)

def _finish(result, t0):
    result['total_latency_ms'] = round((time.time() - t0) * 1000, 1)
    result['id'] = str(uuid.uuid4())[:8]; result['timestamp'] = datetime.utcnow().isoformat(); _record(result); return result

@app.get('/api/health')
def health(): return {'status': 'ok', 'time': datetime.utcnow().isoformat()}
@app.get('/api/history')
def get_history(): return list(reversed(_load_history()))
@app.delete('/api/history')
def clear_history(): _save_history([]); return {'status': 'cleared'}

@app.post('/api/scan')
def scan(req: ScanRequest):
    t0 = time.time(); url = req.url.strip()
    if not url: return {'error': 'URL cannot be empty'}
    lexical, domain, scheme = extract_lexical_host_features(url)
    heuristics = heuristic_url_reasons(lexical, domain, scheme); lookalike = lookalike_check(domain)
    if is_trusted_domain(domain):
        headline = 'Considered safe because the domain is in the trusted-domain registry.'
        return _finish({'url': url, 'domain': domain, 'scheme': scheme, 'mode_requested': req.mode, 'tier0_trusted': True,
            'tier1_5_lookalike': lookalike, 'fast': {'tier': 'Safe', 'risk_score': 0.0, 'proba_legit': 1.0,
            'reasons': [{'feature': 'TrustedDomainRegistry', 'value': domain, 'impact': 0, 'direction': 'lowers risk', 'text': 'the domain is in the trusted registry'}],
            'reason_headline': headline, 'model': 'Tier-0 Trusted Registry', 'latency_ms': .1}, 'deep': None,
            'final_tier': 'Safe', 'final_risk_score': 0.0, 'reason_headline': headline, 'escalated': False, 'fetch_error': None}, t0)
    if lookalike['flagged']:
        reason = {'feature': 'LookalikeDomain', 'value': lookalike['matched_domain'], 'impact': -1.0, 'direction': 'raises risk', 'text': lookalike['reason']}
        reasons = [reason] + heuristics; headline = risk_engine.explanation_headline(lookalike['tier'], reasons, heuristics, lookalike)
        score = 100.0 if lookalike['tier'] == 'Dangerous' else 82.0
        return _finish({'url': url, 'domain': domain, 'scheme': scheme, 'mode_requested': req.mode, 'tier0_trusted': False,
            'tier1_5_lookalike': lookalike, 'fast': {'tier': lookalike['tier'], 'risk_score': score, 'proba_legit': 0.0,
            'reasons': reasons, 'reason_headline': headline, 'model': 'Tier-1.5 Lookalike / Homograph Guard', 'latency_ms': round((time.time()-t0)*1000, 1)},
            'deep': None, 'final_tier': lookalike['tier'], 'final_risk_score': score, 'reason_headline': headline,
            'escalated': False, 'fetch_error': None}, t0)
    fast = risk_engine.score_fast(lexical); fast['reasons'] = heuristics + fast['reasons']; fast['reason_headline'] = risk_engine.explanation_headline(fast['tier'], fast['reasons'], heuristics)
    result = {'url': url, 'domain': domain, 'scheme': scheme, 'mode_requested': req.mode, 'tier0_trusted': False,
        'tier1_5_lookalike': lookalike, 'fast': {**fast, 'latency_ms': round((time.time()-t0)*1000, 1)}, 'deep': None,
        'final_tier': fast['tier'], 'final_risk_score': fast['risk_score'], 'reason_headline': fast['reason_headline'], 'escalated': False, 'fetch_error': None}
    if req.mode == 'deep' or fast['tier'] == 'Suspicious':
        t1 = time.time(); content, meta = extract_content_features(url)
        if meta.get('error'):
            error = meta['error']; result['fetch_error'] = 'page could not be fetched safely: ' + error[:100]
        else:
            deep = risk_engine.score_deep({**lexical, **content}); deep['reasons'] = heuristics + deep['reasons']; deep['reason_headline'] = risk_engine.explanation_headline(deep['tier'], deep['reasons'], heuristics)
            summary = {'page_title': meta.get('title') or '(no title found)', 'has_password_field': bool(content.get('HasPasswordField')),
                'has_hidden_fields': bool(content.get('HasHiddenFields')), 'has_external_form_submit': bool(content.get('HasExternalFormSubmit')),
                'num_iframes': content.get('NoOfiFrame', 0), 'num_redirects': content.get('NoOfURLRedirect', 0), 'num_external_links': content.get('NoOfExternalRef', 0),
                'num_self_links': content.get('NoOfSelfRef', 0), 'num_images': content.get('NoOfImage', 0), 'num_scripts': content.get('NoOfJS', 0),
                'has_favicon': bool(content.get('HasFavicon')), 'is_responsive': bool(content.get('IsResponsive')), 'domain_title_match': content.get('DomainTitleMatchScore', 0),
                'mentions_bank_pay_crypto': bool(content.get('Bank') or content.get('Pay') or content.get('Crypto')), 'has_social_links': bool(content.get('HasSocialNet')),
                'has_copyright_notice': bool(content.get('HasCopyrightInfo')), 'robots_txt_present': bool(content.get('Robots'))}
            result.update({'deep': {**deep, 'latency_ms': round((time.time()-t1)*1000, 1), 'page_title': meta.get('title'), 'content_summary': summary},
                'final_tier': deep['tier'], 'final_risk_score': deep['risk_score'], 'reason_headline': deep['reason_headline'], 'escalated': True})
    return _finish(result, t0)

app.mount('/', StaticFiles(directory=FRONTEND_DIR, html=True), name='frontend')
