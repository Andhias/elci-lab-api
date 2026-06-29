from functools import lru_cache
from pathlib import Path
import re

import httpx
from fastapi import APIRouter, Query

WEB_SEARCH_API = 'https://r.jina.ai/http://duckduckgo.com/html/'

from app.schemas.common import SearchResponse, SearchResult

router = APIRouter(prefix="/search", tags=["search"])

CATALOG_PATH = Path(r"C:/Users/Andhias/Documents/elevator-cloud/catalog.md")
MAX_RESULTS = 50
LOCAL_RESULTS_LIMIT = 30
WEB_RESULTS_LIMIT = 8
WEB_TIMEOUT_SECONDS = 8.0

BRAND_ALIASES = {
    'MONARCH': ['monarch', 'nice', 'wells monarch'],
    'OTIS': ['otis', 'xizi otis'],
    'KONE': ['kone'],
    'SCHINDLER': ['schindler'],
    'MITSUBISHI': ['mitsubishi'],
    'SIGMA': ['sigma', 'lg sigma'],
    'STEP': ['step', 'as320', 'as380'],
    'HYUNDAI': ['hyundai'],
    'FUJITEC': ['fujitec'],
    'FUJI CANNY': ['fuji canny', 'canny'],
    'INVT': ['invt'],
    'SICON': ['sicon'],
    'ARKEL': ['arkel'],
    'BLUELIGHT': ['bluelight', 'bl2000'],
    'HPMONT': ['hpmont', 'mont'],
    'YUNGTAI': ['yungtai', 'yungtay'],
    'NIDEC': ['nidec', 'control techniques'],
    'TYSEEN': ['tyseen'],
    'SMART LIFT': ['smart lift'],
    'AIEC3300': ['aiec3300'],
    'CIBES': ['cibes'],
    'IFE': ['ife'],
    'SIEMENS': ['siemens'],
    'SRH': ['srh'],
    'SWORD': ['sword'],
    'MICO M3': ['mico', 'mico m3'],
    'LOUSERLIFT': ['louserlift'],
    'AE HOSTING': ['hosting', 'ae hosting'],
}

TYPE_HINTS = {
    'error_code': ['error', 'fault', 'kode', 'alarm'],
    'procedure': ['procedure', 'commission', 'debug', 'instruction', 'manual', 'user manual'],
    'document': ['wiring', 'diagram', 'schematic', 'pdf'],
}


@lru_cache(maxsize=1)
def _load_catalog_entries() -> list[dict[str, str]]:
    if not CATALOG_PATH.exists():
        return []

    entries: list[dict[str, str]] = []
    current_section: str | None = None

    for raw_line in CATALOG_PATH.read_text(encoding='utf-8', errors='ignore').splitlines():
        line = raw_line.strip()
        if line.startswith('### '):
            current_section = line[4:].strip()
            continue
        if not current_section or not line.startswith('- `'):
            continue

        try:
            payload, _, size = line[2:].partition(' — ')
            file_path = payload.strip('`')
            title = Path(file_path).name
        except Exception:
            continue

        entries.append(
            {
                'section': current_section,
                'file_path': file_path,
                'title': title,
                'size': size.strip(),
            }
        )

    return entries


def _tokenize(text: str) -> list[str]:
    return [token for token in re.split(r'[^a-z0-9]+', text.lower()) if token]


def _detect_brand(query: str) -> str | None:
    lower = query.lower()
    for brand, aliases in BRAND_ALIASES.items():
        if any(alias in lower for alias in aliases):
            return brand
    return None


def _infer_type(title: str) -> str:
    lower = title.lower()
    if 'error' in lower or 'fault' in lower or re.search(r'\be\d{1,4}\b', lower):
        return 'error_code'
    if any(word in lower for word in ['wiring', 'diagram', 'schematic', 'i-o list']):
        return 'document'
    if any(word in lower for word in ['manual', 'instruction', 'debug', 'commission', 'parameter']):
        return 'procedure'
    return 'document'


def _infer_summary(entry: dict[str, str]) -> str:
    section = entry['section']
    doc_type = _infer_type(entry['title'])
    if doc_type == 'error_code':
        return f'{section} error/fault reference from local library catalog.'
    if doc_type == 'procedure':
        return f'{section} procedure/manual available in local library catalog.'
    return f'{section} document available in local library catalog.'


def _score_entry(entry: dict[str, str], query: str, brand: str | None, query_tokens: list[str]) -> tuple[int, str]:
    section_lower = entry['section'].lower()
    haystack = f"{entry['section']} {entry['title']} {entry['file_path']}".lower()

    score = 0
    match_type = 'Related Match'

    if brand and brand.lower() == section_lower:
        score += 60
        match_type = 'Local Brand Match'

    if query.lower() and query.lower() in haystack:
        score += 120
        match_type = 'Local Exact Match'

    token_hits = sum(1 for token in query_tokens if token in haystack)
    score += token_hits * 18

    if any(hint in haystack for hint in TYPE_HINTS['error_code']) and any(token in ['error', 'fault', 'kode', 'alarm'] for token in query_tokens):
        score += 10
    if any(hint in haystack for hint in TYPE_HINTS['procedure']) and any(token in ['manual', 'procedure', 'debug', 'parameter'] for token in query_tokens):
        score += 10

    if score >= 120:
        confidence = 'high'
    elif score >= 60:
        confidence = 'medium'
    else:
        confidence = 'low'

    return score, f'{match_type}|{confidence}'


def _build_local_result(entry: dict[str, str], score_meta: str, index: int) -> SearchResult:
    match_type, confidence = score_meta.split('|', 1)
    return SearchResult(
        type=_infer_type(entry['title']),
        id=f"local-catalog-{index}",
        title=f"{entry['section']} - {entry['title']}",
        summary=_infer_summary(entry),
        match_type=match_type,
        confidence=confidence,
    )


def _search_local(query: str) -> list[SearchResult]:
    entries = _load_catalog_entries()
    if not query:
        top = entries[: min(20, len(entries))]
        return [
            _build_local_result(entry, 'Local Brand Match|medium', index)
            for index, entry in enumerate(top, start=1)
        ]

    brand = _detect_brand(query)
    query_tokens = _tokenize(query)

    scored: list[tuple[int, dict[str, str], str]] = []
    for entry in entries:
        score, meta = _score_entry(entry, query, brand, query_tokens)
        if score > 0:
            scored.append((score, entry, meta))

    scored.sort(key=lambda item: (-item[0], item[1]['section'], item[1]['title']))
    limited = scored[:LOCAL_RESULTS_LIMIT]
    return [
        _build_local_result(entry, meta, index)
        for index, (_, entry, meta) in enumerate(limited, start=1)
    ]


def _web_query(query: str) -> str:
    trimmed = query.strip()
    if not trimmed:
        return 'elevator escalator controller manuals error codes'
    return f'{trimmed} elevator OR escalator manual OR error code'


def _clean_web_snippet(snippet: str, href: str) -> str:
    text = snippet.strip()
    text = re.sub(r'!\[.*?\]', ' ', text)
    text = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'\1', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text).strip(' -|')
    if not text:
        return href
    return text[:240]


def _search_web(query: str) -> list[SearchResult]:
    search_query = _web_query(query)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36',
    }

    try:
        with httpx.Client(timeout=WEB_TIMEOUT_SECONDS, follow_redirects=True, headers=headers) as client:
            response = client.get(WEB_SEARCH_API, params={'q': search_query})
            response.raise_for_status()
            html = response.text
    except Exception as exc:
        return [
            SearchResult(
                type='web_status',
                id='web-error',
                title='Internet search unavailable',
                summary=f'Web lookup failed: {exc.__class__.__name__}',
                match_type='Web Error',
                confidence='low',
            )
        ]

    pattern = re.compile(
        r'## \[(?P<title>.*?)\]\((?P<href>https?://[^)]+)\)(?P<body>.*?)(?=\n## \[|\Z)',
        re.DOTALL,
    )

    results: list[SearchResult] = []
    seen_titles: set[str] = set()
    for index, match in enumerate(pattern.finditer(html), start=1):
        if len(results) >= WEB_RESULTS_LIMIT:
            break

        title = match.group('title').strip()
        href = match.group('href').strip()
        body = match.group('body').strip()
        if not title or title in seen_titles:
            continue

        lines = [line.strip() for line in body.splitlines() if line.strip()]
        snippet_line = ''
        for line in lines:
            if line.startswith('!['):
                continue
            if 'external-content.duckduckgo.com' in line:
                continue
            if line.startswith('http://duckduckgo.com/l/?uddg='):
                continue
            if line.startswith('http://duckduckgo.com/html'):
                continue
            if line.startswith('[') and '](' in line:
                snippet_line = line
                break
            if len(line) > 20:
                snippet_line = line
                break

        snippet = _clean_web_snippet(snippet_line, href)
        seen_titles.add(title)
        results.append(
            SearchResult(
                type='web_result',
                id=f'web-{index}',
                title=f'WEB - {title}',
                summary=snippet,
                match_type='Internet Result',
                confidence='medium',
            )
        )

    if not results:
        results.append(
            SearchResult(
                type='web_status',
                id='web-empty',
                title='Internet search returned no parsed results',
                summary='Local results are still available, but the web parser found no external matches.',
                match_type='Web Empty',
                confidence='low',
            )
        )

    return results


@router.get('', response_model=SearchResponse)
def search(q: str = Query(default='')) -> SearchResponse:
    query = q.strip()
    local_results = _search_local(query)
    web_results = _search_web(query)

    combined = (local_results + web_results)[:MAX_RESULTS]
    return SearchResponse(query=query, results=combined)
