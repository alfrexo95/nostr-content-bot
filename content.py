import hashlib, json, time, os, sys, re, asyncio, secrets, random, html
import urllib.request
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import xml.etree.ElementTree as ET
import websockets

DRY = "--dry" in sys.argv or os.environ.get("DRY_RUN") == "1"
ADDR = "olivinepug15@primal.net"
RELAYS = ["wss://relay.primal.net", "wss://relay.damus.io", "wss://nos.lol", "wss://relay.snort.social", "wss://offchain.pub"]
DIR = os.path.dirname(os.path.abspath(__file__))
ATOM = "{http://www.w3.org/2005/Atom}"

# --- Meta NIP-75 (Zap Goal) ---
GOAL_AMOUNT_MSATS = 1000000000  # 1,000,000 sats = 1,000,000,000 milisats
GOAL_SUMMARY = "Reach 1,000,000 sats to grow this Nostr profile and support a community under blockade and economic crisis."

# (url, nombre, categoria, exigir_palabras_cripto)
FEEDS = [
    ("https://bitcoinmagazine.com/feed", "Bitcoin Magazine", "news", False),
    ("https://cointelegraph.com/rss", "Cointelegraph", "news", False),
    ("https://decrypt.co/feed", "Decrypt", "news", False),
    ("https://feeds.feedburner.com/CoinDesk", "CoinDesk", "news", False),
    ("https://www.criptonoticias.com/feed/", "CriptoNoticias", "community", False),
    ("https://stacker.news/rss", "Stacker News", "community", False),
    ("https://bitcoinops.org/feed.xml", "Bitcoin Optech", "community", False),
    ("https://bitcoinist.com/feed/", "Bitcoinist", "community", False),
    ("https://hnrss.org/newest?q=bitcoin&points=40", "Hacker News", "buzz", False),
    ("https://hnrss.org/newest?q=nostr&points=10", "Hacker News", "buzz", False),
    ("https://www.theverge.com/rss/index.xml", "The Verge", "buzz", True),
    ("https://www.wired.com/feed/rss", "WIRED", "buzz", True),
]

# --- Fuentes Telegram (scraping web) ---
TG_FEEDS = [
    ("alertamundialnews", "AlertaMundoNews", "news"),
    ("AlertaNews24oficial", "AlertaNews24", "news"),
]

# --- Meta solidaria (1000 USD en sats) ---
MISSION = """🎯 MISSION: Reach 1,000,000 sats (≈ $1000) in zaps to grow this Nostr profile.
Every sat collected will help build tools and content for a community living under blockade and economic crisis.
This is not charity — it's proof that decentralized solidarity works. ⚡
Zap if you believe in a freer world. #Nostr #Bitcoin #Cuba"""

# --- Cuentas destacadas de Nostr (npubs verificados) ---
FEATURED = [
    ("fiatjaf", "nostr:npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6"),
    ("Jack Dorsey", "nostr:npub1sg6plzptd64u62a878hep2kev88swjh3tw00gjs"),
    ("Snowden", "nostr:npub1sn0wdenkukak0d9dfczzeacvhkrgz92ak56egt7vdgzn8pv2wfqqhrjdv9"),
    ("ODELL", "nostr:npub1qny3tkh0acurzla8x3zy4nhrjz5zd8l9sy9jys09umwng00manysew95gx"),
    ("MartyBent", "nostr:npub1guh5grefa7vkay4ps6udxg8lrqxg2kgr3qh9n4gduxut64nfxq0q9y6hjy"),
    ("Cuba Bitcoin", "nostr:npub1huyn6ru55pv6l7p0sxvlu3vfpq7pan958sl4weft0kte6lvdvvksd5s34t"),
    ("DarthCoin", "nostr:npub1lxktpvp5cnq3wl5ctu2x88e30mc0ahh8v47qvzc5dmneqqjrzlkqpm5xlc"),
]

PREFER = ["nostr", "lightning", "bitcoin"]
CRYPTO_WORDS = ["bitcoin", "crypto", "cryptocurrency", "blockchain", "nostr", "lightning", "ethereum", "stablecoin",
                "satoshi", "web3", "decentralized", "privacy", "encryption", "open source"]
BAD = ["airdrop", "giveaway", "presale", "pre-sale", "price prediction", "sponsored", "casino", "promo code",
       "referral", "100x", "to the moon", "pump", "shill", "nsfw"]
BAD_COMMUNITY = ["megathread", "help me", "anyone know", "wtf"]
BASE_TAGS = {"news": ["#Bitcoin", "#CryptoNews"], "community": ["#Bitcoin", "#plebchain"], "buzz": ["#Crypto", "#TechNews"]}
TOPIC_TAGS = {"nostr": ["#nostr", "#grownostr"], "lightning": ["#Lightning", "#Zaps"], "zap": ["#Zaps"],
              "zaps": ["#Zaps"], "ethereum": ["#Ethereum"], "etf": ["#BitcoinETF"], "stablecoin": ["#Stablecoins"],
              "stablecoins": ["#Stablecoins"], "privacy": ["#Privacy"], "halving": ["#Halving"],
              "mining": ["#Mining"], "miners": ["#Mining"], "wallet": ["#SelfCustody"], "regulation": ["#CryptoRegulation"]}
HOOKS = {
    "news": ["Crypto headline:", "Worth a read:", "On the radar today:", "Today in crypto:"],
    "community": ["From the community:", "The community is talking about:", "Trending among Bitcoiners:", "Community pick:"],
    "buzz": ["Tech x crypto:", "Interesting find:", "Caught my eye:", "Worth a look:"],
}
ICONS = {"news": "📰", "community": "💬", "buzz": "🔥"}
QUESTIONS = ["What do you think? 👇", "Thoughts? Reply below 👇", "Agree or disagree? 👇", "Would you use this? 👇"]

X_SUPPORT = "\n\n⚡ Support this news bot with a zap: {addr} #Nostr #Zaps".format(addr=ADDR)

# --- Imágenes y Mensajes de Hype (1 vez por semana) ---
IMAGE_URLS = [
    "https://raw.githubusercontent.com/alfrexo95/nostr-content-bot/main/imagenes/foto1.jpg",
    "https://raw.githubusercontent.com/alfrexo95/nostr-content-bot/main/imagenes/foto2.png",
    "https://raw.githubusercontent.com/alfrexo95/nostr-content-bot/main/imagenes/foto3.jpg",
    "https://raw.githubusercontent.com/alfrexo95/nostr-content-bot/main/imagenes/foto4.jpg",
    "https://raw.githubusercontent.com/alfrexo95/nostr-content-bot/main/imagenes/foto5.jpg",
    "https://raw.githubusercontent.com/alfrexo95/nostr-content-bot/main/imagenes/foto6.jpg",
    "https://raw.githubusercontent.com/alfrexo95/nostr-content-bot/main/imagenes/foto7.jpg",
    "https://raw.githubusercontent.com/alfrexo95/nostr-content-bot/main/imagenes/foto8.jpg",
    "https://raw.githubusercontent.com/alfrexo95/nostr-content-bot/main/imagenes/foto9.jpg",
    "https://raw.githubusercontent.com/alfrexo95/nostr-content-bot/main/imagenes/foto10.jpg",
    "https://raw.githubusercontent.com/alfrexo95/nostr-content-bot/main/imagenes/foto11.png"
]

NOSTR_HYPE_MESSAGES = [
    "Nostr is the protocol for free speech. No censors, no algorithms, just pure human connection. 🔑",
    "Your keys, your identity, your data. Nostr puts the power back in your hands. ⚡",
    "While other networks sell your data, Nostr gives you sovereignty. The future is decentralized. 🌐",
    "Nostr is not just an app, it's a revolution. A global, permissionless network built for freedom. 🚀",
    "No gatekeepers. No banning. Just Bitcoiners, builders, and free thinkers on Nostr. 🛡️",
    "The revolution will not be centralized. Join the Nostr network and own your voice. ✊",
    "Real conversations, real people, real freedom. Nostr is how social media was meant to be. 🤝",
    "Zaps let you put your sats where your values are. Nostr is the value-for-value internet. ⚡",
    "The best thing about Nostr? You can't be deplatformed. Your voice is forever yours. 🗝️",
    "Censorship-resistant. Decentralized. Unstoppable. Welcome to Nostr. 🌍"
]

# --- Curiosities (Duplicadas) ---
CURIOSITIES = [
"Fun fact: Nostr stands for 'Notes and Other Stuff Transmitted by Relays'. No company, no central server, just keys and relays. 🔑 #Nostr #Bitcoin",
"Fun fact: 1 bitcoin is 100,000,000 sats. The smallest unit is named after Satoshi Nakamoto, so every zap is a tiny tribute. ⚡ #Bitcoin #Zaps",
"Fun fact: only 21 million bitcoin will ever exist. That cap is part of the protocol rules, not a company policy. #Bitcoin",
"Fun fact: on May 22, 2010, a programmer paid 10,000 BTC for two pizzas. Bitcoin Pizza Day has been celebrated every year since. 🍕 #Bitcoin",
"Fun fact: Nostr zaps are defined in NIP-57. A zap is a Lightning payment tied to a note or a profile, so a like can carry real value. ⚡ #Nostr #Lightning",
"Fun fact: your npub is your public identity on Nostr and your nsec is your private key. Anyone with your nsec controls your account. 🔑 #Nostr #Security",
"Fun fact: Bitcoin's difficulty adjusts about every two weeks (2,016 blocks) to keep blocks arriving roughly every 10 minutes. ⛏️ #Bitcoin #Mining",
"Fun fact: Bitcoin's block reward halves every 210,000 blocks, roughly every four years. That schedule is called the halving. #Bitcoin",
"Fun fact: the Lightning Network moves payments off-chain between channels, so small payments can settle in seconds with tiny fees. ⚡ #Lightning #Bitcoin",
"Fun fact: on Nostr, relays are simple servers that store and forward notes. You can use many at once and change them anytime. #Nostr",
"Fun fact: a Nostr NIP-05 address looks like an email (name@domain.com) and ties your key to a domain name. #Nostr #NIP05",
"Fun fact: Bitcoin's first block contains a newspaper headline about bank bailouts, a hint about why Bitcoin was created. #Bitcoin",
"Fun fact: Nostr was started by a pseudonymous developer known as fiatjaf, and it keeps growing through open proposals called NIPs. #Nostr",
"Fun fact: relays don't actually know who you are unless your client tells them. Nostr is pseudonymous by design. 🎭 #Nostr",
"Fun fact: Satoshi Nakamoto's last known public message was in December 2010. Since then, the network runs on its own. 👻 #Bitcoin",
"Fun fact: Lightning Network channel capacities are public, but individual balances are private. It's a layer of privacy. 🕵️ #Lightning",
"Fun fact: NIP-05 is basically DNS for Nostr. It proves you own a domain without exposing your private keys. #Nostr #NIP05",
"Fun fact: Bitcoin mining is just guessing a number repeatedly until you get the right hash. It's proof of work. 🎲 #Bitcoin",
"Fun fact: every Lightning payment requires two nodes to have a channel with enough liquidity. It's a routing game. 🚦 #Lightning",
"Fun fact: cold wallets are immune to remote hacks because the private keys never touch the internet. 🧊 #Bitcoin #Security",
"Fun fact: Nostr is built on cryptography, not trust. You don't need to trust a server to verify a signature. 🔐 #Nostr",
"Fun fact: Bitcoin has 8 decimal places. The smallest unit is a satoshi, but you can divide a satoshi off-chain on Lightning. ⚡ #Bitcoin",
"Fun fact: you can run a Nostr relay on a Raspberry Pi. It's incredibly lightweight. 🍓 #Nostr",
"Fun fact: Zaps are just Lightning invoices with a Nostr event attached. It's a clever way to combine two protocols. 🧩 #Nostr #Lightning",
"Fun fact: the Nostr logo is a key because it represents your control over your identity and data. 🗝️ #Nostr",
"Fun fact: Bitcoin's consensus is Nakamoto Consensus. It solved the Byzantine Generals' Problem. 🏛️ #Bitcoin"
]

# --- Jokes (Duplicadas) ---
JOKES = [
"Why did the Nostr user cross the road? To reach a better relay. 😄 #Nostr",
"I told my relay a joke. It stored it, forwarded it to everyone, and I still didn't get a zap. #Nostr #Zaps",
"My nsec and I have a perfect relationship. I never show it to anyone. 🔑 #Nostr",
"How do you know someone runs a full node? Don't worry, they'll tell you. 😅 #Bitcoin",
"Zaps: the only 'like' button where people really put their sats where their mouth is. ⚡ #Nostr #Zaps",
"Roses are red, sats are small, a zap on this note is the best gift of all. ⚡ #Nostr",
"A Bitcoiner's favorite workout? Stacking sats. Rest day? Never. 💪 #Bitcoin",
"Other apps: 'You may like this.' Nostr: 'You choose your feed.' 😎 #Nostr",
"Me: 'I'll just check Nostr for a minute.' Also me, three hours later, still zapping. ⚡ #Nostr",
"Why don't relays get lonely? Someone is always forwarding them messages. #Nostr",
"Why did the Bitcoiner break up with the bank? Because it was too centralized. 🏦 #Bitcoin",
"A Lightning Network walks into a bar. The bartender says, 'What's the rush?' ⚡ #Lightning",
"What's a Bitcoiner's favorite dance? The HODL. 💃 #Bitcoin",
"Why are Nostr users so good at keeping secrets? They know the value of an nsec. 🤫 #Nostr",
"What do you call a Bitcoin that never moves? A HODLer's retirement fund. 💎🙌 #Bitcoin",
"Why did the relay server go to therapy? Too many unresolved notes. 🛋️ #Nostr",
"What's the difference between a Bitcoiner and a magician? One makes money disappear, the other makes it appear. 🎩 #Bitcoin",
"How many Bitcoiners does it take to change a lightbulb? None, they just wait for the halving to make it shine brighter. 💡 #Bitcoin",
"What's a pizza's favorite crypto? Bitcoin, of course. 🍕 #BitcoinPizzaDay",
"Why don't Bitcoiners ever get lost? Because they always follow the whitepaper. 📜 #Bitcoin"
]

# --- Tips (Duplicadas) ---
TIPS = [
"Tip: back up your nsec offline (paper or a password manager). If you lose it, nobody can recover your account. #Nostr #Security",
"Tip: use a signer app like Amber on Android so your nsec isn't stored in every Nostr app you try. #Nostr #Amber",
"Tip: add a Lightning address to your Nostr profile so people can zap you. It works like an email address for sats. ⚡ #Nostr #Lightning",
"Tip: connect a wallet with NWC (Nostr Wallet Connect) to zap from different apps without moving funds around. #Nostr #Lightning",
"Tip: set a spending limit on every wallet connection you create. If it leaks, your loss is capped. 🔒 #Lightning #Security",
"Tip: use several relays. If one goes down, your notes still reach your followers. #Nostr",
"Tip: never paste your seed phrase or nsec into a website. Real wallets and apps never ask for it in a chat. #Bitcoin #Security",
"Tip: new on Nostr? Say hi with #introductions and follow a few accounts in your interests. The feed is yours. #grownostr",
"Tip: when sending bitcoin to a new address, send a small test amount first. Mistakes can't be undone. #Bitcoin",
"Tip: Lightning wallets differ: some hold your funds for you, others give you the keys. Know which one you use. ⚡ #Lightning #SelfCustody",
"Tip: Use a hardware wallet for long-term storage. 'Not your keys, not your coins.' 🔐 #Bitcoin #Security",
"Tip: Nostr isn't just for crypto. Share your hobbies, art, and thoughts. It's a social network for everyone. 🎨 #Nostr",
"Tip: Lightning addresses (name@domain) make zapping as easy as sending an email. ⚡ #Lightning",
"Tip: Be careful with public Wi-Fi when accessing wallets. Use a VPN or mobile data. 📶 #Security",
"Tip: Review your relay list periodically. Some relays go offline or change their policies. 🔄 #Nostr",
"Tip: You can use NIP-05 to verify your identity. It's the blue checkmark of Nostr, but decentralized. ✔️ #Nostr",
"Tip: Always verify the receiving address before sending sats. Copy-paste errors happen. 👀 #Bitcoin",
"Tip: Zaps are public by default, but you can send private zaps if you want to tip anonymously. 🕵️ #Zaps",
"Tip: Set a strong password for your email, as it's the backup for many services. 🔑 #Security",
"Tip: Contribute to the community by running your own relay. It helps the network grow. 🌐 #Nostr"
]

ASKS = [
"If this account makes your feed better, a zap helps keep the posts coming. Thank you for the support! ⚡ {addr} #Nostr #Zaps",
"Enjoying these crypto and Nostr posts? Zap, repost or reply: all three help more than you think. ⚡ {addr} #Nostr",
"Small zaps add up. If a post made you smile or learn something today, send a few sats my way. ⚡ {addr} #Zaps #Bitcoin",
]
CYCLE = ["curiosity", "joke", "tip", "curiosity", "joke", "tip", "curiosity", "ask"]

p = 2**256 - 2**32 - 977
n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)

def add(P, Q):
    if P is None: return Q
    if Q is None: return P
    if P[0] == Q[0] and (P[1] + Q[1]) % p == 0: return None
    l = 3 * P[0] * P[0] * pow(2 * P[1], -1, p) % p if P == Q else (Q[1] - P[1]) * pow(Q[0] - P[0], -1, p) % p
    x = (l * l - P[0] - Q[0]) % p
    return (x, (l * (P[0] - x) - P[1]) % p)

def mul(P, k):
    R = None
    while k:
        if k & 1: R = add(R, P)
        P = add(P, P); k >>= 1
    return R

def th(tag, *b):
    t = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(t + t + b"".join(b)).digest()

def nsec_to_hex(s):
    C = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
    acc = bits = 0; out = []
    for c in s[5:-6]:
        acc = (acc << 5) | C.index(c); bits += 5
        while bits >= 8:
            bits -= 8; out.append((acc >> bits) & 255)
        acc &= (1 << bits) - 1
    return bytes(out).hex()

def sign(msg, sk):
    d = int(sk, 16); P = mul(G, d)
    if P[1] % 2: d = n - d
    px = P[0].to_bytes(32, 'big')
    t = (d ^ int.from_bytes(th("BIP0340/aux", secrets.token_bytes(32)), 'big')).to_bytes(32, 'big')
    k = int.from_bytes(th("BIP0340/nonce", t, px, msg), 'big') % n
    R = mul(G, k)
    if R[1] % 2: k = n - k
    rx = R[0].to_bytes(32, 'big')
    e = int.from_bytes(th("BIP0340/challenge", rx, px, msg), 'big') % n
    return (rx + ((k + e * d) % n).to_bytes(32, 'big')).hex()

def make_event(sk, content, kind=1, extra_tags=None):
    tags = [["t", t.lower()] for t in re.findall(r"#(\w+)", content)]
    if extra_tags:
        tags.extend(extra_tags)
    pub = mul(G, int(sk, 16))[0].to_bytes(32, 'big').hex()
    ts = int(time.time())
    raw = json.dumps([0, pub, ts, kind, tags, content], separators=(',', ':'), ensure_ascii=False)
    eid = hashlib.sha256(raw.encode()).digest()
    return {"id": eid.hex(), "pubkey": pub, "created_at": ts, "kind": kind, "tags": tags, "content": content, "sig": sign(eid, sk)}

def make_goal_event(sk):
    """Crea el evento NIP-75 (kind 9041) para la meta de 1,000,000 sats."""
    content = MISSION
    tags = [
        ["relays"] + RELAYS,
        ["amount", str(GOAL_AMOUNT_MSATS)],
        ["summary", GOAL_SUMMARY],
    ]
    pub = mul(G, int(sk, 16))[0].to_bytes(32, 'big').hex()
    ts = int(time.time())
    raw = json.dumps([0, pub, ts, 9041, tags, content], separators=(',', ':'), ensure_ascii=False)
    eid = hashlib.sha256(raw.encode()).digest()
    return {"id": eid.hex(), "pubkey": pub, "created_at": ts, "kind": 9041, "tags": tags, "content": content, "sig": sign(eid, sk)}

async def send(url, ev):
    try:
        async with websockets.connect(url, open_timeout=30) as ws:
            await ws.send(json.dumps(["EVENT", ev]))
            r = json.loads(await asyncio.wait_for(ws.recv(), 20))
            print(url, r)
            return bool(r[0] == "OK" and r[2])
    except Exception as e:
        print(url, "error:", e)
        return False

def get_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; nostr-content-bot/1.0)"})
    return urllib.request.urlopen(req, timeout=25).read()

def fetch_telegram_channel(channel):
    """Descarga la página web de un canal de Telegram y extrae los mensajes."""
    url = f"https://t.me/s/{channel}"
    try:
        data = get_url(url).decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"TG {channel} error: {e}")
        return []
    blocks = re.findall(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', data, re.DOTALL)
    out = []
    for b in blocks:
        text = re.sub(r"<br\s*/?>", "\n", b)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 15:
            continue
        post = re.search(r'data-post="([^"]+)"', data)
        link = f"https://t.me/{channel}" if not post else f"https://t.me/{post.group(1)}"
        out.append((text, link))
    return out[:10]

def clean(t):
    t = html.unescape(re.sub(r"<[^>]+>", " ", t or ""))
    return re.sub(r"\s+", " ", t).strip()

def clean_link(l):
    u = urlparse(l.strip())
    q = [(k, v) for k, v in parse_qsl(u.query) if not k.startswith("utm_") and k not in ("at_medium", "at_campaign", "ref", "fbclid")]
    return urlunparse(u._replace(query=urlencode(q), fragment=""))

def parse_feed(data):
    root = ET.fromstring(data)
    out = []
    for it in root.iter("item"):
        out.append((clean(it.findtext("title")), (it.findtext("link") or "").strip()))
    for it in root.iter(ATOM + "entry"):
        link = ""
        for l in it.findall(ATOM + "link"):
            if l.get("rel") in (None, "alternate"):
                link = l.get("href") or ""; break
        out.append((clean(it.findtext(ATOM + "title")), link.strip()))
    return out

def has_word(low, w):
    return re.search(r"\b" + re.escape(w) + r"\b", low) is not None

def tags_for(title, cat):
    low = title.lower()
    tags = list(BASE_TAGS[cat])
    for k, ts in TOPIC_TAGS.items():
        if has_word(low, k): tags += ts
    seen, out = set(), []
    for t in tags:
        if t.lower() not in seen:
            seen.add(t.lower()); out.append(t)
    return " ".join(out[:5])

def pick(cat, seen):
    pool = []
    for url, name, c, need_kw in FEEDS:
        if c != cat: continue
        try:
            items = parse_feed(get_url(url))
        except Exception as e:
            print(name, "error:", e); continue
        taken = 0
        for title, link in items:
            if taken >= 8: break
            link = clean_link(link); low = title.lower()
            if len(title) < 15 or len(title) > 220 or not link or link in seen: continue
            if any(b in low for b in BAD): continue
            if cat == "community" and any(b in low for b in BAD_COMMUNITY): continue
            if need_kw and not any(has_word(low, w) for w in CRYPTO_WORDS): continue
            score = sum(2 if k == "nostr" else 1 for k in PREFER if has_word(low, k))
            pool.append((score, title, link, name)); taken += 1

    for channel, name, c in TG_FEEDS:
        if c != cat: continue
        items = fetch_telegram_channel(channel)
        taken = 0
        for title, link in items:
            if taken >= 5: break
            low = title.lower()
            if len(title) < 15 or len(title) > 280 or not link or link in seen: continue
            if any(b in low for b in BAD): continue
            score = 3
            pool.append((score, title, link, name)); taken += 1

    if not pool: return None
    best = max(x[0] for x in pool)
    score, title, link, name = random.choice([x for x in pool if x[0] == best])
    text = random.choice(HOOKS[cat]) + "\n\n" + ICONS[cat] + " " + title + "\n" + link + "\n\nvia " + name
    if cat != "news":
        text += "\n\n" + random.choice(QUESTIONS)
    if any(name == tg_name for _, tg_name, _ in TG_FEEDS):
        hashtags = re.findall(r"#(\w+)", title)
        base = ["#Bitcoin", "#CryptoNews", "#Breaking"]
        seen_ht = set()
        ht_list = []
        for h in hashtags + base:
            if h.lower() not in seen_ht:
                seen_ht.add(h.lower()); ht_list.append("#" + h)
        text += " " + " ".join(ht_list[:6])
        text += X_SUPPORT
    else:
        text += "\n" + tags_for(title, cat)
    text += "\n\n" + MISSION
    mention_list = " ".join([f"{name} ({npub})" for name, npub in FEATURED[:5]])
    text += "\n\nFollow these Nostr leaders: " + mention_list
    return {"text": text, "link": link}

def evergreen(st):
    kind = CYCLE[st["n"] % len(CYCLE)]
    pool = {"curiosity": CURIOSITIES, "joke": JOKES, "tip": TIPS, "ask": ASKS}[kind]
    idx = st["idx"].get(kind, 0)
    text = pool[idx % len(pool)]
    st["idx"][kind] = idx + 1
    if kind == "ask": text = text.format(addr=ADDR)
    elif idx % 2 == 0: text += "\n\n⚡ " + ADDR
    text += "\n\n" + MISSION
    mention_list = " ".join([f"{name} ({npub})" for name, npub in FEATURED[:5]])
    text += "\n\nFollow these Nostr leaders: " + mention_list
    return text

def image_post(st):
    """Publica una imagen solo los lunes (1 vez por semana) con un mensaje aleatorio."""
    if time.localtime().tm_wday != 0:
        return None
        
    if not IMAGE_URLS:
        return None
        
    idx = st.get("img_idx", 0) % len(IMAGE_URLS)
    img_url = IMAGE_URLS[idx]
    st["img_idx"] = idx + 1
    
    phrase = random.choice(NOSTR_HYPE_MESSAGES)
    
    text = phrase + "\n\n" + img_url + "\n\n" + MISSION
    mention_list = " ".join([f"{name} ({npub})" for name, npub in FEATURED[:5]])
    text += "\n\nFollow these Nostr leaders: " + mention_list
    return {"text": text, "link": None}

def load():
    path = os.path.join(DIR, "state.json")
    s = json.load(open(path)) if os.path.exists(path) else {}
    s.setdefault("seen", []); s.setdefault("n", 0); s.setdefault("idx", {})
    s.setdefault("goal_id", None); s.setdefault("img_idx", 0)
    return s

async def main():
    st = load(); seen = set(st["seen"]); posts = []
    nsec = os.environ.get("NOSTR_NSEC", "").strip()
    if not nsec and not DRY:
        print("Falta el secreto NOSTR_NSEC"); return
    sk = nsec_to_hex(nsec) if nsec else None

    # --- Publicar o recuperar el evento de meta NIP-75 ---
    goal_id = st.get("goal_id")
    if not goal_id and sk:
        goal_ev = make_goal_event(sk)
        print("Publicando evento de meta NIP-75...")
        results = await asyncio.gather(*[send(r, goal_ev) for r in RELAYS])
        if any(results):
            goal_id = goal_ev["id"]
            st["goal_id"] = goal_id
            print("✅ Meta publicada con id:", goal_id)
        else:
            print("⚠️ No se pudo publicar la meta en ningún relay")
    elif goal_id:
        print("ℹ️ Usando meta existente:", goal_id)

    news = pick("news", seen)
    if news: posts.append(news); seen.add(news["link"])
    order = ["community", "buzz"] if st["n"] % 2 == 0 else ["buzz", "community"]
    for cat in order:
        it = pick(cat, seen)
        if it:
            posts.append(it); seen.add(it["link"]); break
    posts.append({"text": evergreen(st), "link": None})

    # --- Añadir la imagen si es Lunes ---
    img = image_post(st)
    if img:
        posts.append(img)

    if DRY:
        for x in posts: print("[DRY]\n" + x["text"] + "\n")
        return

    for i, x in enumerate(posts):
        if i: await asyncio.sleep(45)
        extra = [["goal", goal_id]] if goal_id else []
        ev = make_event(sk, x["text"], kind=1, extra_tags=extra)
        ok = any(await asyncio.gather(*[send(r, ev) for r in RELAYS]))
        if ok and x["link"]: st["seen"] = (st["seen"] + [x["link"]])[-400:]
        print("Publicada" if ok else "No se publico", "->", x["text"][:60].replace("\n", " "))
    st["n"] += 1
    json.dump(st, open(os.path.join(DIR, "state.json"), "w"), indent=1)

asyncio.run(main())
