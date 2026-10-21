"""Builds the published pages from the bilingual sources in _src/.

_src/index.html and _src/about.html hold both languages side by side
(<span data-l="en"> / <span data-l="ru">). This script writes one page per
language so each URL has a single language for search engines:

  index.html, about.html        English
  ru/index.html, ru/about.html  Russian

Run from the repo root:  python3 _build.py
Folders and files starting with "_" are not published by GitHub Pages.
"""
import os, re
from html.parser import HTMLParser

from _brands import BRANDS

SITE = 'https://foreignauto.shop/'
# Google Analytics 4 measurement ID (looks like G-XXXXXXXXXX). Empty means no analytics on the site.
GA_ID = ''

# Loads GA4 and reports taps on phone, text and Instagram links and booking form sends as events.
GA_SNIPPET = '''<script async src="https://www.googletagmanager.com/gtag/js?id={id}"></script>
<script>
window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}
gtag('js',new Date());gtag('config','{id}');
document.addEventListener('click',function(e){{var a=e.target.closest&&e.target.closest('a[href]');if(!a)return;var h=a.getAttribute('href');
  if(h.indexOf('tel:')===0)gtag('event','phone_call',{{link_url:h}});
  else if(h.indexOf('sms:')===0)gtag('event','text_message',{{link_url:h}});
  else if(h.indexOf('instagram.com')>-1)gtag('event','instagram_click');
  else if(h.indexOf('google.com/maps')>-1)gtag('event','get_directions');}});
document.addEventListener('submit',function(e){{if(e.target.id==='book')gtag('event','generate_lead',{{form:'book'}})}});
</script>
'''
HERE = os.path.dirname(os.path.abspath(__file__))

META = {
    ('index', 'en'): ('Auto Repair in Aurora, CO | Foreign Auto 5280',
        'Honest car repair in Aurora, CO. 25 years fixing Japanese, Korean, European and American cars. Photos and a written estimate before any work, 12-month warranty. Call (720) 937-3445.'),
    ('about', 'en'): ('About Us | Foreign Auto 5280, Auto Repair in Aurora, CO',
        'Meet Foreign Auto 5280, an owner-run repair shop in the Mission Viejo area of Aurora, CO. 25 years of experience, service in English and Russian, 12-month warranty.'),
    ('index', 'ru'): ('Русский автосервис в Авроре и Денвере | Foreign Auto 5280',
        'Автосервис с русскоговорящим мастером в Авроре, Колорадо, рядом с Денвером. 25 лет ремонтируем японские, корейские, европейские и американские машины. Фото и смета до ремонта, гарантия 12 месяцев. (720) 937-3445.'),
    ('about', 'ru'): ('О нас | Foreign Auto 5280, русский автосервис в Авроре, CO',
        'Foreign Auto 5280: небольшой автосервис в районе Mission Viejo в Авроре, Колорадо. Владелец сам работает в цеху, говорим по-русски и по-английски, 25 лет опыта, гарантия 12 месяцев.'),
}

RU_ATTRS = {
    'alt="Gloved hand fitting a brake caliper over the rotor"': 'alt="Мастер ставит тормозной суппорт на диск"',
    'alt="Gloved hand holding a combination wrench over the tool chest"': 'alt="Рука в перчатке с гаечным ключом над ящиком с инструментами"',
    'alt="Impact wrench on the lug nuts of a steel wheel"': 'alt="Гайковёрт на колёсных гайках стального диска"',
    'alt="Mechanic checking engine oil with the dipstick"': 'alt="Механик проверяет уровень масла щупом"',
    'alt="Mechanic checking tire pressure on a Honda raised on the lift"': 'alt="Механик проверяет давление в шине Honda на подъёмнике"',
    'alt="Mechanic removing the front wheel of a white sedan on a lift at Foreign Auto 5280"': 'alt="Механик снимает переднее колесо белого седана на подъёмнике в Foreign Auto 5280"',
    'alt="Mechanic setting tire pressure on a Honda on the lift"': 'alt="Механик накачивает шину Honda на подъёмнике"',
    'alt="New brake rotor and caliper on a raised car"': 'alt="Новый тормозной диск и суппорт на поднятой машине"',
    'alt="Owner of Foreign Auto 5280 in the shop"': 'alt="Владелец Foreign Auto 5280 в цеху"',
    'alt="Owner of Foreign Auto 5280 standing by the lift in the shop"': 'alt="Владелец Foreign Auto 5280 у подъёмника в цеху"',
    'alt="Plugging a puncture in a tire tread"': 'alt="Ремонт прокола в протекторе шины"',
    'alt="Rows of sockets in the tool chest"': 'alt="Ряды торцевых головок в ящике с инструментами"',
    'aria-label="Book diagnostics"': 'aria-label="Записаться на диагностику"',
    'aria-label="Contact"': 'aria-label="Связаться"',
    'aria-label="Example repair order"': 'aria-label="Пример заказ-наряда"',
    'aria-label="Language"': 'aria-label="Язык"',
    'aria-label="Main"': 'aria-label="Основное меню"',
    'aria-label="Menu"': 'aria-label="Меню"',
    'aria-label="Rated 5.0 out of 5"': 'aria-label="Оценка 5.0 из 5"',
    'Mechanic removing the front wheel of a white sedan at Foreign Auto 5280': 'Механик снимает переднее колесо белого седана в Foreign Auto 5280',
}


class Strip(HTMLParser):
    """Finds the source ranges of elements whose data-l is not the target language."""
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}

    def __init__(self, src, lang):
        super().__init__(convert_charrefs=False)
        self.lines = [0]
        for line in src.splitlines(keepends=True):
            self.lines.append(self.lines[-1] + len(line))
        self.lang, self.cuts, self.stack = lang, [], []

    def off(self):
        ln, col = self.getpos()
        return self.lines[ln - 1] + col

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            return
        drop = any(k == 'data-l' and v != self.lang for k, v in attrs)
        self.stack.append((tag, self.off() if drop else None))

    def handle_endtag(self, tag):
        while self.stack:
            t, start = self.stack.pop()
            if t == tag:
                if start is not None:
                    self.cuts.append((start, self.off() + len(f'</{tag}>')))
                return


def strip_lang(src, lang):
    p = Strip(src, lang)
    p.feed(src)
    out, pos = [], 0
    for a, b in sorted(p.cuts):
        if a < pos:
            continue
        out.append(src[pos:a])
        pos = b
    out.append(src[pos:])
    return ''.join(out).replace(f' data-l="{lang}"', '')


class URLs(dict):
    def __missing__(self, key):
        page, lang = key
        return SITE + ('ru/' if lang == 'ru' else '') + ('' if page == 'index' else page + '.html')


def build(page, lang, src=None):
    s = src if src is not None else open(os.path.join(HERE, '_src', page + '.html'), encoding='utf-8').read()
    s = strip_lang(s, lang)
    url = URLs()
    title, desc = META[(page, lang)]
    s = re.sub(r'<title>.*?</title>', f'<title>{title}</title>', s, count=1)
    s = re.sub(r'(<meta (?:name="description"|property="og:description") content=")[^"]*"', lambda m: m.group(1) + desc + '"', s)
    s = re.sub(r'(<meta property="og:title" content=")[^"]*"', lambda m: m.group(1) + title + '"', s)
    s = re.sub(r'(<link rel="canonical" href=")[^"]*"', lambda m: m.group(1) + url[(page, lang)] + '"', s)
    s = re.sub(r'(<meta property="og:url" content=")[^"]*"', lambda m: m.group(1) + url[(page, lang)] + '"', s)
    alt = ('<link rel="alternate" hreflang="en" href="%s">\n<link rel="alternate" hreflang="ru" href="%s">\n'
           '<link rel="alternate" hreflang="x-default" href="%s">\n') % (url[(page, 'en')], url[(page, 'ru')], url[(page, 'en')])
    s = s.replace('<meta name="robots"', alt + '<meta name="robots"', 1)
    if page != 'index':
        s = re.sub(r'("@type": "AboutPage", "url": ")[^"]*(", "name": ")[^"]*"', lambda m: m.group(1) + url[(page, lang)] + m.group(2) + title + '"', s)
    # language switch becomes links between the two versions
    links = {'en': url[(page, 'en')].replace(SITE, '/'), 'ru': url[(page, 'ru')].replace(SITE, '/')}
    sw = ('<div class="lang" role="group" aria-label="Language">\n'
          f'        <a href="{links["en"]}" hreflang="en" lang="en"{" aria-current=\"true\"" if lang == "en" else ""}>EN</a>\n'
          f'        <a href="{links["ru"]}" hreflang="ru" lang="ru"{" aria-current=\"true\"" if lang == "ru" else ""}>RU</a>\n'
          '      </div>')
    s = re.sub(r'<div class="lang" role="group" aria-label="Language">.*?</div>', sw, s, count=1, flags=re.S)
    s = s.replace('.lang button{', '.lang a{text-decoration:none;display:inline-flex;align-items:center;justify-content:center;').replace('.lang button[aria-pressed="true"]', '.lang a[aria-current]').replace('.lang button', '.lang a')
    js_old = re.search(r"  var root=document\.documentElement.*?  set\(start\);\n", s, flags=re.S).group(0)
    js_new = ("  try{localStorage.setItem('fa-lang','%s')}catch(e){}\n" % lang)
    if lang == 'en':
        js_new += "  if(location.hash==='#ru')location.replace('%s'+(location.search||''));\n" % links['ru']
    s = s.replace(js_old, js_new)
    if lang == 'ru':
        s = s.replace('<html lang="en">', '<html lang="ru">')
        s = s.replace('<meta property="og:locale" content="en_US">\n<meta property="og:locale:alternate" content="ru_RU">',
                      '<meta property="og:locale" content="ru_RU">\n<meta property="og:locale:alternate" content="en_US">')
        for a, b in RU_ATTRS.items():
            s = s.replace(a, b)
        # pages live one folder down
        s = s.replace('src="img/', 'src="../img/').replace('url(img/', 'url(../img/')
    if GA_ID:
        s = s.replace('</head>', GA_SNIPPET.format(id=GA_ID) + '</head>', 1)
    out = os.path.join(HERE, ('ru/' if lang == 'ru' else '') + page + '.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write(s)
    return out


def span(en, ru):
    return f'<span data-l="en">{en}</span><span data-l="ru">{ru}</span>'


def brand_source(b):
    """A make page: the about page's header, footer and scripts around new content."""
    shell = open(os.path.join(HERE, '_src', 'about.html'), encoding='utf-8').read()
    head, rest = shell.split('<main id="top">', 1)
    foot = rest.split('</main>', 1)[1]
    head = head.replace(' aria-current="page"', '')
    head = head.replace('"@type": "AboutPage"', '"@type": "WebPage"')
    name = b['name'] + (' and ' + b['also'] if b['also'] else '')
    name_ru = b['name'].replace(' and ', ' и ') + (' и ' + b['also'] if b['also'] else '')
    models = ''.join(f'<li>{m}</li>' for m in b['models'])
    jobs = ''.join(f'<div class="val"><h3>{span(j[0], j[2])}</h3><p>{span(j[1], j[3])}</p></div>' for j in b['jobs'])
    others = ''.join(f'<a class="make" href="{o["slug"]}.html">{span(o["name"], o["name"].replace(" and ", " и "))}</a>'
                     for o in BRANDS if o is not b)
    main = f'''<main id="top">
 <div class="hero-zone backdrop" style="--bd:url(img/bg-shop.jpg)">
  <div class="wrap about-hero">
    <div class="ah-grid">
      <div>
        <p class="eyebrow">{span('Makes we fix · ' + name, 'Какие марки чиним · ' + name_ru)}</p>
        <h1 style="margin-top:20px">{span(*b['h1'])}</h1>
        <p class="lede" style="margin-top:20px">{span(*b['lede'])}</p>
        <div class="cta" style="margin-top:28px">
          <a class="btn btn-main" href="tel:+17209373445">{span('Call (720) 937-3445', 'Позвонить (720) 937-3445')}</a>
          <a class="btn btn-line" href="./#book">{span('Book a visit', 'Записаться')}</a>
        </div>
      </div>
      <figure class="photo"><img src="img/{b['photo']}" alt="{b['photo_alt'][0]}" fetchpriority="high"></figure>
    </div>
  </div>
 </div>

  <section>
    <div class="wrap">
      <div class="sec-head">
        <p class="eyebrow">{span('What we see most', 'С чем приезжают чаще всего')}</p>
        <h2>{span('Common ' + b['name'] + ' jobs <em>we handle</em>', 'Частые работы <em>по ' + name_ru.split(' и ')[0] + '</em>')}</h2>
      </div>
      <div class="values bp-jobs">{jobs}</div>
    </div>
  </section>

  <section class="band">
    <div class="wrap makes-split bp-models">
      <div class="sec-head" style="margin:0">
        <p class="eyebrow">{span('Models', 'Модели')}</p>
        <h2>{span(name + ' models <em>we work on</em>', 'Модели ' + name_ru + ', <em>которые мы чиним</em>')}</h2>
        <p>{span('Every repair starts with photos and a written estimate sent to your phone. Work begins only after your OK, and parts and labor carry a 12-month warranty.', 'Любой ремонт начинается с фото и письменной сметы на ваш телефон. К работе приступаем только после вашего согласия, а на запчасти и работу даём гарантию 12 месяцев.')}</p>
      </div>
      <ul class="mk-list">{models}</ul>
    </div>
  </section>

  <section>
    <div class="wrap">
      <div class="sec-head">
        <p class="eyebrow">{span('Other makes', 'Другие марки')}</p>
        <h2>{span('Driving something else?', 'У вас другая машина?')}</h2>
        <p>{span('We also fix Mazda, Mercedes-Benz, BMW, Audi, Volkswagen, Chevrolet, Jeep, Ram and every other make except electric cars.', 'Ещё чиним Mazda, Mercedes-Benz, BMW, Audi, Volkswagen, Chevrolet, Jeep, Ram и любые другие марки, кроме электромобилей.')}</p>
      </div>
      <div class="makes">{others}<a class="make" href="./#makes">{span('All makes', 'Все марки')}</a></div>
    </div>
  </section>
</main>'''
    return head + main + foot


def add_brand_meta(b):
    META[(b['slug'], 'en')] = (b['title'][0], b['desc'][0])
    META[(b['slug'], 'ru')] = (b['title'][1], b['desc'][1])
    RU_ATTRS['alt="%s"' % b['photo_alt'][0]] = 'alt="%s"' % b['photo_alt'][1]


def write_sitemap(pages):
    url = URLs()
    rows = []
    for page in pages:
        alts = ''.join(f'\n    <xhtml:link rel="alternate" hreflang="{l}" href="{url[(page, l)]}"/>' for l in ('en', 'ru'))
        for lang in ('en', 'ru'):
            rows.append(f'  <url>\n    <loc>{url[(page, lang)]}</loc>{alts}\n  </url>')
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
           + '\n'.join(rows) + '\n</urlset>\n')
    open(os.path.join(HERE, 'sitemap.xml'), 'w', encoding='utf-8').write(xml)


if __name__ == '__main__':
    for page in ('index', 'about'):
        for lang in ('en', 'ru'):
            print('wrote', os.path.relpath(build(page, lang), HERE))
    for b in BRANDS:
        add_brand_meta(b)
        src = brand_source(b)
        for lang in ('en', 'ru'):
            print('wrote', os.path.relpath(build(b['slug'], lang, src), HERE))
    write_sitemap(['index', 'about'] + [b['slug'] for b in BRANDS])
    print('wrote sitemap.xml')
