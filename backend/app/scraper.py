"""Scrape product title, main image, and manufacturer from a URL."""
import json
import re
from urllib.parse import urljoin, urlparse


def _split_proxy_auth(proxy_url: str | None):
    """Parse proxy URL into (clean_url, (user, password)) or (url, None).

    curl_cffi with impersonate mode doesn't forward credentials embedded
    in the proxy URL during the CONNECT tunnel — they must be passed
    separately via proxy_auth.
    """
    if not proxy_url:
        return proxy_url, None
    parsed = urlparse(proxy_url)
    if parsed.username:
        port = f":{parsed.port}" if parsed.port else ""
        clean = f"{parsed.scheme}://{parsed.hostname}{port}"
        return clean, (parsed.username, parsed.password or "")
    return proxy_url, None

try:
    import httpx
    from bs4 import BeautifulSoup
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

try:
    from curl_cffi import requests as cffi_requests
    _CFFI_OK = True
except ImportError:
    _CFFI_OK = False

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


def scrape_product(url: str, cookie_1688: str | None = None) -> dict:
    if not _DEPS_OK:
        return {"title": None, "image": None, "manufacturer": None, "error": "scraping deps not installed"}

    if "1688.com" in url:
        return _scrape_1688(url, cookie_1688)

    return _scrape_generic(url)


def _scrape_generic(url: str) -> dict:
    from app.config import settings
    proxy_url = settings.PROXY_URL or None
    try:
        client_kwargs = dict(timeout=10, follow_redirects=True, headers=HEADERS)
        if proxy_url:
            client_kwargs["proxy"] = proxy_url
        with httpx.Client(**client_kwargs) as client:
            resp = client.get(url)
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        title = (
            _meta(soup, "og:title")
            or _meta(soup, "twitter:title")
            or (soup.title.string.strip() if soup.title and soup.title.string else None)
        )
        image = (
            _meta(soup, "og:image")
            or _meta(soup, "twitter:image")
            or _first_img(soup)
        )
        if image and not image.startswith(("http://", "https://")):
            image = urljoin(url, image)
        manufacturer = (
            _meta(soup, "product:brand")
            or _meta(soup, "og:site_name")
            or _meta(soup, "author")
            or _json_ld_brand(soup)
        )

        if title:
            title = re.sub(r"\s+", " ", title).strip()[:255]
        if manufacturer:
            manufacturer = re.sub(r"\s+", " ", manufacturer).strip()[:100]

        return {"title": title, "image": image, "manufacturer": manufacturer}
    except Exception as e:
        return {"title": None, "image": None, "manufacturer": None, "error": str(e)}


def _scrape_1688(url: str, cookie_override: str | None = None) -> dict:
    """Scrape 1688.com using configured cookies (login required)."""
    from app.config import settings

    cookie_str = cookie_override or settings.COOKIE_1688
    if not cookie_str:
        return {
            "title": None, "image": None, "manufacturer": None,
            "error": "未配置1688 Cookie，请在系统设置中配置（管理员 -> 系统设置 -> 1688 Cookie）",
        }

    if not _CFFI_OK:
        return {
            "title": None, "image": None, "manufacturer": None,
            "error": "curl_cffi 未安装",
        }

    try:
        proxy_url = settings.PROXY_URL or None
        proxy_clean, proxy_auth = _split_proxy_auth(proxy_url)
        resp = cffi_requests.get(
            url,
            impersonate="chrome120",
            timeout=15,
            headers={
                **HEADERS,
                "Referer": "https://www.1688.com/",
                "Cookie": cookie_str,
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-site",
            },
            proxies={"http": proxy_clean, "https": proxy_clean} if proxy_clean else None,
            proxy_auth=proxy_auth,
        )
        resp.raise_for_status()
        html = resp.text

        if "punish-component" in html or "g.alicdn.com/sd/punish" in html:
            return {
                "title": None, "image": None, "manufacturer": None,
                "error": "1688 触发了安全验证（人机检测），请稍后重试或更换IP/Cookie",
            }

        if len(html) < 10000 and ("login" in html.lower() or "signin" in html):
            return {
                "title": None, "image": None, "manufacturer": None,
                "error": "1688 Cookie 已失效，请重新配置",
            }

        soup = BeautifulSoup(html, "html.parser")
        title = None
        image = None
        manufacturer = None

        # --- Title ---
        raw_title = None
        if soup.title and soup.title.string:
            raw_title = soup.title.string.strip()
        if not raw_title:
            raw_title = _meta(soup, "og:title") or _meta(soup, "twitter:title")
        if raw_title:
            for suffix in ["-1688.com", "-阿里巴巴", "- 阿里巴巴"]:
                if raw_title.endswith(suffix):
                    raw_title = raw_title[: -len(suffix)].strip()
            parts = raw_title.rsplit("-", 1)
            title = parts[0].strip()
            if len(parts) >= 2:
                manufacturer = parts[-1].strip()

        # --- Image from meta tags ---
        image = _meta(soup, "og:image") or _meta(soup, "twitter:image")
        if image and image.startswith("//"):
            image = "https:" + image

        # --- Extract from embedded JSON / script data ---
        if not image:
            img_patterns = [
                r'"imageUrl"\s*:\s*"((?:https?:)?//[^"]+)"',
                r'"imgUrl"\s*:\s*"((?:https?:)?//[^"]+)"',
                r'"originalImageURI"\s*:\s*"((?:https?:)?//[^"]+)"',
                r'"searchImageUrl"\s*:\s*"((?:https?:)?//[^"]+)"',
                r'"image"\s*:\s*"((?:https?:)?//[^"]+alicdn\.com[^"]*)"',
            ]
            for pattern in img_patterns:
                m = re.search(pattern, html)
                if m:
                    image = m.group(1)
                    if image.startswith("//"):
                        image = "https:" + image
                    break

        # --- Try alicdn img tags ---
        if not image:
            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                if src and "alicdn.com" in src and not src.endswith((".gif", ".ico")):
                    if src.startswith("//"):
                        src = "https:" + src
                    image = src
                    break

        # --- Manufacturer from script data ---
        if not manufacturer:
            company_patterns = [
                r'"companyName"\s*:\s*"([^"]+)"',
                r'"supplierName"\s*:\s*"([^"]+)"',
                r'"sellerName"\s*:\s*"([^"]+)"',
            ]
            for pattern in company_patterns:
                m = re.search(pattern, html)
                if m:
                    manufacturer = m.group(1)
                    break

        if title:
            title = re.sub(r"\s+", " ", title).strip()[:255]
        if manufacturer:
            manufacturer = re.sub(r"\s+", " ", manufacturer).strip()[:100]

        return {"title": title, "image": image, "manufacturer": manufacturer}
    except Exception as e:
        return {"title": None, "image": None, "manufacturer": None, "error": str(e)}


# ---- shared helpers ----

def _first_img(soup) -> str | None:
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or img.get("data-original")
        if not src or src.startswith("data:"):
            continue
        try:
            w = int(img.get("width", 0) or 0)
            h = int(img.get("height", 0) or 0)
            if (w and w < 80) or (h and h < 80):
                continue
        except (ValueError, TypeError):
            pass
        return src
    return None


def _meta(soup, property_name: str) -> str | None:
    tag = soup.find("meta", property=property_name) or soup.find("meta", attrs={"name": property_name})
    if tag and tag.get("content"):
        return tag["content"].strip() or None
    return None


def _json_ld_brand(soup) -> str | None:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                data = data[0]
            brand = data.get("brand")
            if isinstance(brand, dict):
                return brand.get("name")
            if isinstance(brand, str):
                return brand
        except Exception:
            pass
    return None


def scrape_all_images(url: str, cookie_override: str | None = None) -> dict:
    """Scrape main carousel images and SKU variant (color/size/spec) images from 1688.
    Excludes description/detail images.
    """
    if "1688.com" not in url:
        return {"error": "仅支持1688链接"}

    from app.config import settings

    cookie_str = cookie_override or settings.COOKIE_1688
    if not cookie_str:
        return {"error": "未配置1688 Cookie"}

    if not _CFFI_OK:
        return {"error": "curl_cffi 未安装"}

    try:
        proxy_url = settings.PROXY_URL or None
        proxy_clean, proxy_auth = _split_proxy_auth(proxy_url)
        resp = cffi_requests.get(
            url,
            impersonate="chrome120",
            timeout=15,
            headers={
                **HEADERS,
                "Referer": "https://www.1688.com/",
                "Cookie": cookie_str,
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-site",
            },
            proxies={"http": proxy_clean, "https": proxy_clean} if proxy_clean else None,
            proxy_auth=proxy_auth,
        )
        resp.raise_for_status()
        html = resp.text

        if "punish-component" in html or "g.alicdn.com/sd/punish" in html:
            return {"error": "1688 触发了安全验证，请稍后重试或更换Cookie"}

        result: list = []

        def _normalize_alicdn(u: str) -> str:
            """提取 alicdn 图片的核心标识，去掉尺寸/质量/格式后缀用于去重。"""
            u = u.split('?')[0]
            u = re.sub(r'_\d{1,4}x\d{1,4}', '', u)
            u = re.sub(r'_q\d+', '', u)
            u = re.sub(r'\._\.\w+$', '', u)
            u = re.sub(r'\.(\w+)_\.\w+$', r'.\1', u)
            return u

        def _url_size(u: str) -> int:
            """从URL中提取尺寸数字，用于比较大小。无尺寸后缀视为原图，返回最大值。"""
            m = re.search(r'_(\d{1,4})x(\d{1,4})', u)
            if m:
                return int(m.group(1)) * int(m.group(2))
            return 99999999  # 无尺寸后缀 = 原图，最大

        seen_keys: dict = {}  # key -> index in result

        def add(u: str):
            if not u:
                return
            if u.startswith("//"):
                u = "https:" + u
            # Strip size suffix to get original quality
            u = re.sub(r'_\d{2,4}x\d{2,4}\.(jpg|jpeg|png|webp)', r'.\1', u, flags=re.IGNORECASE)
            if "alicdn.com" not in u:
                return
            if u.endswith((".gif", ".ico", ".svg")):
                return
            if re.search(r'_\d{1,2}x\d{1,2}\.', u):  # skip tiny icons
                return
            key = _normalize_alicdn(u)
            if key in seen_keys:
                # 保留更大尺寸的
                idx = seen_keys[key]
                if _url_size(u) > _url_size(result[idx]):
                    result[idx] = u
            else:
                seen_keys[key] = len(result)
                result.append(u)

        # 1. Main product carousel images from named list fields
        for pattern in [
            r'"imageList"\s*:\s*\[([^\]]*)\]',
            r'"subjectImageList"\s*:\s*\[([^\]]*)\]',
            r'"mainImages"\s*:\s*\[([^\]]*)\]',
            r'"coverImages"\s*:\s*\[([^\]]*)\]',
        ]:
            for m in re.finditer(pattern, html):
                for u in re.findall(r'"((?:https?:)?//[^"]+)"', m.group(1)):
                    add(u)

        # Single main/cover image fields
        for pattern in [
            r'"mainImage"\s*:\s*"((?:https?:)?//[^"]+)"',
            r'"coverImage"\s*:\s*"((?:https?:)?//[^"]+)"',
            r'"originalImageURI"\s*:\s*"((?:https?:)?//[^"]+)"',
            r'"searchImageUrl"\s*:\s*"((?:https?:)?//[^"]+)"',
        ]:
            for m in re.finditer(pattern, html):
                add(m.group(1))

        # 2. SKU variant images (color/size/spec) — inside propValues arrays
        for pv_m in re.finditer(r'"propValues"\s*:', html):
            chunk = html[pv_m.start(): pv_m.start() + 8000]
            bracket_start = chunk.find('[')
            if bracket_start == -1:
                continue
            # Match the closing bracket with depth tracking
            depth = 0
            end_idx = -1
            for i, ch in enumerate(chunk[bracket_start:], bracket_start):
                if ch == '[':
                    depth += 1
                elif ch == ']':
                    depth -= 1
                    if depth == 0:
                        end_idx = i
                        break
            if end_idx == -1:
                continue
            block = chunk[bracket_start: end_idx + 1]
            for u in re.findall(r'"(?:imageUrl|picUrl|imgUrl)"\s*:\s*"((?:https?:)?//[^"]+)"', block):
                add(u)

        return {"urls": result}
    except Exception as e:
        return {"error": str(e)}
