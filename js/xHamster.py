#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xHamster 兼容影视仓/OK影视
镜像: zh.xhamster1.pw
播放: 仅输出 h264 具体分辨率，禁止 _TPL_/av1 粘连
"""
import json
import re
import sys
import urllib.parse

try:
    import requests
except ImportError:
    requests = None

sys.path.append('../../')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""):
            pass


class Spider(BaseSpider):
    def __init__(self):
        self.siteUrl = 'https://zh.xhamster1.pw'
        self.hosts = [
            'https://zh.xhamster1.pw',
            'https://xhamster1.pw',
            'https://zh.xhamster.com',
            'https://xhamster.com',
        ]
        self.userAgent = (
            'Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36'
        )
        self.channels = {
            'newest': {'name': '最新', 'path': '/newest'},
            'best': {'name': '最佳', 'path': '/best'},
            '4k': {'name': '4K超清', 'path': '/4k'},
            'hd': {'name': '高清HD', 'path': '/hd'},
            'categories-asian': {'name': '亚洲', 'path': '/categories/asian'},
            'categories-japanese': {'name': '日本', 'path': '/categories/japanese'},
            'categories-chinese': {'name': '中国', 'path': '/categories/chinese'},
            'categories-korean': {'name': '韩国', 'path': '/categories/korean'},
            'categories-japanese-vintage': {'name': '日本复古', 'path': '/search/japanese+vintage'},
            'categories-european-vintage': {'name': '欧美复古', 'path': '/search/european+vintage'},
            'categories-chinese-classic': {'name': '中国经典', 'path': '/search/chinese+classic'},
            'categories-italian-vintage': {'name': '意大利复古', 'path': '/search/italian+vintage'},
            'categories-milf': {'name': '熟女', 'path': '/categories/milf'},
            'categories-amateur': {'name': '业余', 'path': '/categories/amateur'},
            'categories-anal': {'name': '肛交', 'path': '/categories/anal'},
            'categories-vintage': {'name': '复古', 'path': '/categories/vintage'},
        }

    def getName(self):
        return 'xHamster'

    def init(self, extend=""):
        try:
            if extend:
                if isinstance(extend, str) and extend.startswith('http'):
                    self.siteUrl = extend.rstrip('/')
                else:
                    ext = json.loads(extend) if isinstance(extend, str) else (extend or {})
                    if isinstance(ext, dict) and ext.get('host'):
                        self.siteUrl = str(ext.get('host')).rstrip('/')
        except Exception:
            pass
        return self

    def _hdr(self):
        return {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Origin': self.siteUrl,
            'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cookie': 'age_verified=1; cookie_accept=1; locale=zh; ts_popunder=1',
        }

    def fetch(self, url, headers=None):
        if headers is None:
            headers = self._hdr()
        urls = [url]
        for h in self.hosts:
            if url.startswith(self.siteUrl):
                alt = h + url[len(self.siteUrl):]
                if alt not in urls:
                    urls.append(alt)
            elif not url.startswith('http'):
                alt = h + (url if url.startswith('/') else '/' + url)
                if alt not in urls:
                    urls.append(alt)
        for u in urls:
            try:
                if requests:
                    resp = requests.get(u, headers=headers, timeout=22, verify=False)
                    if resp.status_code == 200 and len(resp.text) > 3000:
                        for h in self.hosts:
                            if u.startswith(h):
                                self.siteUrl = h
                                break
                        return resp.text
            except Exception:
                continue
        return ''

    def _abs(self, u):
        if not u:
            return ''
        if u.startswith('http'):
            return u
        if u.startswith('//'):
            return 'https:' + u
        return self.siteUrl + (u if u.startswith('/') else '/' + u)

    def _page_url(self, path, pg=1):
        path = path or '/newest'
        if not path.startswith('/'):
            path = '/' + path
        url = self.siteUrl + path
        if int(pg or 1) > 1:
            url += ('&' if '?' in url else '?') + 'page=' + str(pg)
        return url

    def _extract_initials(self, html):
        html = html or ''
        idx = html.find('window.initials')
        if idx < 0:
            return None
        brace = html.find('{', idx)
        if brace < 0:
            return None
        depth = 0
        in_str = False
        esc = False
        quote = ''
        for i in range(brace, min(len(html), brace + 600000)):
            ch = html[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == quote:
                    in_str = False
                continue
            if ch in ('"', "'"):
                in_str = True
                quote = ch
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(html[brace:i + 1].replace('\\/', '/'))
                    except Exception:
                        try:
                            return json.loads(html[brace:i + 1])
                        except Exception:
                            return None
        return None

    def _videos_from_initials(self, data):
        videos, seen = [], set()
        if not data:
            return videos

        def fix_thumb(u):
            """保留原始签名 URL，不改尺寸不编码（编码后部分壳仍无法加载）"""
            if not u:
                return ''
            return str(u).replace('\\/', '/').strip()

        def push(slug, title, pic):
            if not slug or slug in seen or len(str(slug)) < 4:
                return
            if re.match(r'^(categories|channels|users|photos|creators|pornstars|tags|search|shorts)\b', str(slug), re.I):
                return
            # 过滤 shorts
            if '/shorts/' in str(slug) or str(slug).startswith('shorts'):
                return
            seen.add(slug)
            videos.append({
                'vod_id': str(slug),
                'vod_name': (title or str(slug).replace('-', ' '))[:120],
                'vod_pic': self._abs(fix_thumb(pic)),
                'vod_remarks': '',
            })

        candidates = []

        def collect(obj, depth=0):
            if depth > 12:
                return
            if isinstance(obj, list):
                # 列表本身可能是 video 对象数组
                if obj and isinstance(obj[0], dict) and (
                    obj[0].get('pageURL') or obj[0].get('thumbURL') or obj[0].get('title')
                ):
                    candidates.extend(obj)
                for x in obj[:80]:
                    collect(x, depth + 1)
                return
            if not isinstance(obj, dict):
                return
            # 任何层级的 videoThumbProps
            vtp = obj.get('videoThumbProps')
            if isinstance(vtp, list) and vtp:
                candidates.extend(vtp)
            # 分类页: trendingVideoListProps / videoListProps / searchResult 等
            for key in (
                'videos', 'videoList', 'videoThumbProps',
                'relatedVideoProps', 'trendingVideoProps', 'trendingVideoListProps',
                'recommendedVideoProps', 'videoListProps', 'searchResult',
                'layoutPage', 'store', 'entity', 'pages',
            ):
                if key in obj:
                    collect(obj[key], depth + 1)
            # 兜底：遍历其余 dict 值（限深度）
            if depth < 6:
                for k, v in obj.items():
                    if k in ('videos', 'videoList', 'videoThumbProps', 'relatedVideoProps',
                             'trendingVideoProps', 'trendingVideoListProps',
                             'recommendedVideoProps', 'videoListProps', 'searchResult',
                             'layoutPage', 'store', 'entity', 'pages'):
                        continue
                    if isinstance(v, (dict, list)):
                        collect(v, depth + 1)

        collect(data)

        for obj in candidates:
            if not isinstance(obj, dict):
                continue
            pageURL = obj.get('pageURL') or obj.get('link') or obj.get('url') or ''
            title = obj.get('title') or obj.get('name') or ''
            slug = ''
            if isinstance(pageURL, str) and '/videos/' in pageURL:
                slug = pageURL.split('/videos/')[-1].split('?')[0].rstrip('/')
            elif isinstance(pageURL, str) and '/shorts/' in pageURL:
                continue
            if not slug:
                continue
            pic = (
                obj.get('imageURL')
                or obj.get('thumbURL')
                or obj.get('previewThumbURL')
                or obj.get('image')
                or ''
            )
            push(slug, title, pic)

        return videos

    def _parse_list(self, html):
        html = html or ''
        data = self._extract_initials(html)
        videos = self._videos_from_initials(data)
        if len(videos) >= 40:
            return videos
        seen = {v['vod_id'] for v in videos}
        patterns = [
            r'href="(/videos/([^"?#]+))"[^>]*>[\s\S]{0,800}?(?:src|data-src|data-thumb)=["\']([^"\']+)["\'][\s\S]{0,500}?(?:alt|title)=["\']([^"\']*)["\']',
            r'(?:src|data-src)=["\']([^"\']+xhcdn[^"\']+)["\'][\s\S]{0,400}?href="[^"]*/videos/([^"?#]+)"[\s\S]{0,300}?(?:alt|title)=["\']([^"\']*)["\']',
        ]
        for pat in patterns:
            for m in re.finditer(pat, html, re.I):
                g = m.groups()
                if len(g) == 4 and g[0].startswith('/videos'):
                    slug, pic, title = g[1], g[2], g[3]
                elif len(g) == 3:
                    pic, slug, title = g[0], g[1], g[2]
                else:
                    continue
                slug = slug.strip('/')
                if not slug or slug in seen or len(slug) < 4:
                    continue
                if re.match(r'^(categories|channels|users|photos|creators|pornstars|tags|search|shorts)\b', slug, re.I):
                    continue
                seen.add(slug)
                # keep original signed size
                pass
                # pic unchanged
                videos.append({
                    'vod_id': slug,
                    'vod_name': (title or slug.replace('-', ' '))[:120],
                    'vod_pic': self._abs(pic),
                    'vod_remarks': '',
                })
            if len(videos) >= 24:
                break
        if len(videos) < 12:
            for m in re.finditer(
                r'(?:src|data-src)=["\'](https://[^"\']*xhcdn[^"\']+)["\'][\s\S]{0,500}?/videos/([a-z0-9][a-z0-9\-_]{5,})',
                html, re.I
            ):
                pic, slug = m.group(1), m.group(2)
                if slug in seen:
                    continue
                if re.match(r'^(categories|channels|users|photos|creators|pornstars|tags|search|shorts)\b', slug, re.I):
                    continue
                seen.add(slug)
                videos.append({
                    'vod_id': slug,
                    'vod_name': slug.replace('-', ' '),
                    'vod_pic': self._abs(pic),
                    'vod_remarks': '',
                })
            for m in re.finditer(r'/videos/([a-z0-9][a-z0-9\-_]{5,})', html, re.I):
                slug = m.group(1)
                if slug in seen:
                    continue
                if re.match(r'^(categories|channels|users|photos|creators|pornstars|tags|search|shorts)\b', slug, re.I):
                    continue
                seen.add(slug)
                block = html[max(0, m.start()-300):m.start()+100]
                pm = re.search(r'(https://[^"\']*xhcdn[^"\']+\.(?:webp|jpg|jpeg|png)[^"\']*)', block, re.I)
                videos.append({
                    'vod_id': slug,
                    'vod_name': slug.replace('-', ' '),
                    'vod_pic': self._abs(pm.group(1)) if pm else '',
                    'vod_remarks': '',
                })
        return videos

    def homeContent(self, filter=False):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        try:
            lst = self._parse_list(self.fetch(self._page_url('/newest', 1)))[:48]
        except Exception:
            lst = []
        return {'class': classes, 'list': lst, 'filters': {}}

    def homeVideoContent(self):
        return {'list': self._parse_list(self.fetch(self._page_url('/newest', 1)))[:24]}

    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        pg = int(pg or 1)
        tid = str(tid or 'newest').strip()
        info = self.channels.get(tid, {'path': '/' + tid if not tid.startswith('/') else tid})
        path = info.get('path') or '/newest'
        paths = [path]
        if path.startswith('/search/'):
            alt = path.replace('+', '%20')
            if alt not in paths:
                paths.append(alt)
        videos, html = [], ''
        for p in paths:
            html = self.fetch(self._page_url(p, pg))
            videos = self._parse_list(html)
            if len(videos) >= 8:
                break
        if len(videos) < 5 and tid not in ('newest', 'best'):
            html2 = self.fetch(self._page_url('/newest', 1))
            videos2 = self._parse_list(html2)
            if len(videos2) > len(videos):
                videos = videos2
        pagecount = pg + 1 if len(videos) >= 12 else pg
        return {
            'list': videos or [],
            'page': pg,
            'pagecount': pagecount,
            'limit': 48,
            'total': pagecount * 48 if videos else 0,
        }

    def searchContent(self, key, quick=False, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick=False, pg=1):
        pg = int(pg or 1)
        raw = str(key or '').strip()
        if not raw:
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 48, 'total': 0}
        q_plus = urllib.parse.quote(raw).replace('%20', '+')
        candidates = [
            '%s/search/%s' % (self.siteUrl, q_plus) + (('?page=%d' % pg) if pg > 1 else ''),
            '%s/search/?q=%s' % (self.siteUrl, urllib.parse.quote(raw)) + (('&page=%d' % pg) if pg > 1 else ''),
        ]
        videos, html = [], ''
        for url in candidates:
            html = self.fetch(url)
            videos = self._parse_list(html)
            if videos:
                break
        return {
            'list': videos or [],
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 12 else pg,
            'limit': 48,
            'total': 9999 if videos else 0,
        }

    def _pick_plays(self, html):
        """只返回 h264 具体分辨率，禁止 _TPL_ / av1"""
        html = html or ''
        plays = []
        seen = set()

        def clean(u):
            u = (u or '').replace('\\/', '/').replace('\\u002F', '/')
            if len(u) > 10 and 'http' in u[8:]:
                u = u[:u.find('http', 8)]
            return u.strip().split()[0] if u else ''

        def add(label, u):
            u = clean(u)
            if not u or not u.startswith('http') or u in seen:
                return
            if '_TPL_' in u or re.search(r'preview|sprite|thumb', u, re.I):
                return
            if 'av1' in u.lower():
                return
            seen.add(u)
            plays.append((label, u))

        raw = [clean(u) for u in re.findall(r'https?://[^"\'\s<>\\]+\.m3u8[^"\'\s<>\\]*', html)]
        tpl = None
        for u in raw:
            if '_TPL_' in u and 'h264' in u:
                tpl = u
                break
        if not tpl:
            for u in raw:
                if '_TPL_' in u:
                    tpl = re.sub(r'_TPL_\.(?:h264|av1)\.mp4\.m3u8', '_TPL_.h264.mp4.m3u8', u)
                    break

        qualities = []
        if tpl and 'multi=' in tpl:
            mm = re.search(r'multi=([^/&]+)', tpl)
            if mm:
                qualities = re.findall(r'(\d+p)', mm.group(1), re.I)
                qualities = sorted(set(qualities), key=lambda q: int(re.sub(r'\D', '', q) or 0), reverse=True)

        if tpl:
            for q in (qualities or ['1080p', '720p', '480p']):
                add(q, tpl.replace('_TPL_', q))

        for u in raw:
            if '_TPL_' in u or 'av1' in u.lower():
                continue
            qm = re.search(r'(\d+p)', u, re.I)
            add(qm.group(1) if qm else 'HLS', u)

        return plays

    def detailContent(self, ids):
        slug = str((ids or [''])[0]).lstrip('/')
        if slug.startswith('videos/'):
            slug = slug[7:]
        slug = slug.split('?')[0].split('#')[0]
        page = self.siteUrl + '/videos/' + slug
        html = self.fetch(page)
        title = slug.replace('-', ' ')
        pic = ''
        tm = re.search(r'og:title["\']\s+content=["\']([^"\']+)', html or '', re.I)
        if not tm:
            tm = re.search(r'<title>([^<]+)</title>', html or '', re.I)
        if tm:
            title = re.sub(r'\s*[-|].*$', '', tm.group(1)).strip() or title
        pm = re.search(r'og:image["\']\s+content=["\']([^"\']+)', html or '', re.I)
        if pm:
            pic = self._abs(pm.group(1))
        plays = self._pick_plays(html)
        if plays:
            # 单线路 + # 多清晰度，避免部分壳 $$$ 粘连
            play_from = 'xHamster'
            play_url = '#'.join(['%s$%s' % (n, u) for n, u in plays])
        else:
            play_from = 'xHamster'
            play_url = '正片$%s' % slug
        return {
            'list': [{
                'vod_id': slug,
                'vod_name': title,
                'vod_pic': pic,
                'vod_content': title,
                'vod_play_from': play_from,
                'vod_play_url': play_url,
            }]
        }

    def playerContent(self, flag, id, vipFlags=None):
        header = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Origin': self.siteUrl,
            'Accept': '*/*',
        }

        def clean(u):
            u = (u or '').replace('\\/', '/').strip()
            if len(u) > 10 and 'http' in u[8:]:
                u = u[:u.find('http', 8)]
            u = u.strip().split()[0] if u else ''
            if '_TPL_' in u:
                u = re.sub(r'_TPL_\.(?:h264|av1)', '720p.h264', u)
            return u

        play_id = str(id or '').strip()
        if play_id.startswith('//'):
            play_id = 'https:' + play_id
        if '$' in play_id and not play_id.startswith('http'):
            play_id = play_id.split('$')[-1].strip()
        play_id = clean(play_id)

        if play_id.startswith('http') and self.isVideoFormat(play_id):
            return {'parse': 0, 'jx': 0, 'url': play_id, 'playUrl': '', 'header': header}

        slug = play_id.split('|')[0]
        if slug.startswith('videos/'):
            slug = slug[7:]
        slug = slug.split('?')[0].split('#')[0]
        page = self.siteUrl + '/videos/' + slug
        html = self.fetch(page)
        plays = self._pick_plays(html)
        if plays:
            flag_s = str(flag or '')
            chosen = plays[0][1]
            for n, u in plays:
                if flag_s and (flag_s == n or flag_s in n or n in flag_s):
                    chosen = u
                    break
            # 优先 720p
            if not flag_s or flag_s in ('xHamster', '正片', ''):
                for n, u in plays:
                    if n == '720p':
                        chosen = u
                        break
            return {'parse': 0, 'jx': 0, 'url': clean(chosen), 'playUrl': '', 'header': header}

        return {'parse': 1, 'jx': '1', 'url': page, 'playUrl': '', 'header': header}

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower()
        return any(x in u for x in ('.m3u8', '.mp4', '.webm', '/hls/'))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    spider = Spider()
    spider.init()
    r = spider.categoryContent('newest', 1)
    print('list', len(r.get('list') or []))
    if r.get('list'):
        d = spider.detailContent([r['list'][0]['vod_id']])
        item = d['list'][0]
        print('from', item['vod_play_from'])
        print('url', item['vod_play_url'][:120])
        print('TPL', '_TPL_' in item['vod_play_url'])
        pc = spider.playerContent('720p', item['vod_play_url'].split('#')[0].split('$')[-1])
        print('pc', pc['url'][:90])
