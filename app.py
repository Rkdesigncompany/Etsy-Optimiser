import streamlit as st
import requests
import pandas as pd
import re
from collections import Counter
import copy

st.set_page_config(page_title="Etsy Optimizer", page_icon="🛍️", layout="centered", initial_sidebar_state="collapsed")

# Simple mobile detection via User-Agent (works on Streamlit Cloud / recent versions)
def is_mobile():
    try:
        ua = st.context.headers.get("User-Agent", "").lower()
        return any(x in ua for x in ["iphone", "android", "mobile", "ipad"])
    except Exception:
        return False

mobile = is_mobile()

st.title("🛍️ Etsy Optimizer")
st.caption("Phone-friendly • Demo or connect your shop")

# ---------- Demo data ----------
DEMO_LISTINGS = [
    {
        "listing_id": 1001,
        "title": "Beautiful Handmade Ceramic Coffee Mug Perfect Gift for Her Birthday Anniversary",
        "description": "This is a mug. It is pretty. Buy it.",
        "tags": ["mug", "ceramic", "gift", "coffee"],
        "price": {"amount": 2499, "divisor": 100, "currency_code": "USD"},
        "views": 120,
        "num_favorers": 8,
        "quantity": 15,
        "state": "active",
        "url": "https://www.etsy.com/listing/demo1",
        "images": [{"url_570xN": "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=570", "rank": 1, "alt_text": ""}],
        "materials": ["ceramic"],
        "who_made": "i_did",
        "when_made": "made_to_order"
    },
    {
        "listing_id": 1002,
        "title": "Blue Speckled Stoneware Mug",
        "description": "Hand-thrown blue speckled stoneware mug, perfect for your morning coffee. Made from durable stoneware clay with a food-safe glaze. Holds 12 oz. Dishwasher safe. Great gift for coffee lovers, dad, or anyone who enjoys unique pottery. Each piece is one of a kind. Handmade in small batches.",
        "tags": ["blue ceramic mug", "handmade pottery", "coffee lover gift", "stoneware mug", "unique mug gift", "wheel thrown mug", "kitchen decor", "dad gift mug", "speckled mug", "artisan coffee cup", "pottery mug", "morning coffee", "housewarming gift"],
        "price": {"amount": 3200, "divisor": 100, "currency_code": "USD"},
        "views": 450,
        "num_favorers": 32,
        "quantity": 3,
        "state": "active",
        "url": "https://www.etsy.com/listing/demo2",
        "images": [{"url_570xN": "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?w=570", "rank": 1, "alt_text": "Blue speckled mug"}],
        "materials": ["stoneware", "glaze"],
        "who_made": "i_did",
        "when_made": "made_to_order"
    },
    {
        "listing_id": 1003,
        "title": "Custom Name Necklace Personalized Gift Jewelry Gold",
        "description": "Beautiful necklace with custom name. Perfect gift.",
        "tags": ["necklace", "gold", "personalized", "gift for her", "custom name"],
        "price": {"amount": 4500, "divisor": 100, "currency_code": "USD"},
        "views": 80,
        "num_favorers": 3,
        "quantity": 20,
        "state": "active",
        "url": "https://www.etsy.com/listing/demo3",
        "images": [{"url_570xN": "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=570", "rank": 1, "alt_text": ""}],
        "materials": ["gold"],
        "who_made": "i_did",
        "when_made": "made_to_order"
    },
    {
        "listing_id": 1004,
        "title": "Minimalist Wall Art Print Botanical",
        "description": "High quality botanical print. Ready to frame.",
        "tags": ["wall art", "botanical", "print", "minimalist", "home decor", "plant", "poster"],
        "price": {"amount": 1800, "divisor": 100, "currency_code": "USD"},
        "views": 210,
        "num_favorers": 15,
        "quantity": 0,
        "state": "active",
        "url": "https://www.etsy.com/listing/demo4",
        "images": [{"url_570xN": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=570", "rank": 1, "alt_text": "Botanical print"}],
        "materials": ["paper"],
        "who_made": "i_did",
        "when_made": "2020_2024"
    }
]

def price_usd(listing):
    p = listing.get("price") or {}
    return p.get("amount", 0) / (p.get("divisor", 100) or 100)

def analyze_listing(listing):
    title = listing.get("title") or ""
    tags = listing.get("tags") or []
    description = listing.get("description") or ""
    images = listing.get("images") or []
    qty = listing.get("quantity", 0)
    
    issues, suggestions = [], []
    score = 100
    word_count = len(title.split())
    
    if word_count > 15:
        issues.append(f"Title {word_count} words (aim <15)")
        score -= 15
        suggestions.append("Shorten title. Lead with the product.")
    if word_count < 5:
        issues.append("Title too short")
        score -= 8
    
    words = [w.lower() for w in title.split()]
    if len(words) != len(set(words)):
        issues.append("Repeated words in title")
        score -= 10
    
    if re.match(r"^(beautiful|perfect|amazing|stunning|lovely|gorgeous)\b", title.lower()):
        issues.append("Starts with adjective")
        score -= 12
        suggestions.append("Move adjectives to description.")
    
    if len(tags) < 13:
        issues.append(f"{len(tags)}/13 tags")
        score -= 20
        suggestions.append("Fill all 13 tags with phrases.")
    
    if len(tags) != len(set(tags)):
        issues.append("Duplicate tags")
        score -= 8
    
    single = [t for t in tags if " " not in t]
    if len(single) > 4:
        issues.append(f"{len(single)} single-word tags")
        score -= 10
    
    title_l = title.lower()
    if any(t.lower() in title_l for t in tags):
        issues.append("Tags repeat title phrases")
        score -= 8
    
    if len(description) < 250:
        issues.append("Short description")
        score -= 10
    
    if not images:
        issues.append("No images")
        score -= 20
    else:
        if not images[0].get("alt_text"):
            issues.append("Main image missing alt text")
            score -= 5
        if len(images) < 5:
            issues.append(f"Only {len(images)} images")
            score -= 8
    
    if not listing.get("materials"):
        issues.append("No materials")
        score -= 5
    
    if qty == 0:
        issues.append("Out of stock")
        score -= 15
    elif qty <= 3:
        issues.append(f"Low stock ({qty})")
        score -= 5
    
    score = max(0, min(100, score))
    return {
        "score": score,
        "issues": issues,
        "suggestions": suggestions,
        "word_count": word_count,
        "tag_count": len(tags),
        "image_count": len(images),
        "quantity": qty,
        "price": price_usd(listing)
    }

def suggest_keywords(listing):
    text = ((listing.get("title") or "") + " " + (listing.get("description") or "")).lower()
    words = re.findall(r"\b[a-z]{3,}\b", text)
    common = [w for w, _ in Counter(words).most_common(10)]
    base = ["handmade", "gift for her", "personalized", "custom", "unique", "artisan", "birthday gift"]
    ideas = []
    for w in common[:3]:
        if w not in ["the", "and", "for", "with"]:
            ideas += [f"{w} gift", f"handmade {w}"]
    ideas += [b for b in base if b not in text]
    return list(dict.fromkeys(ideas))[:10]

def generate_better_title(listing):
    title = listing.get("title") or ""
    cleaned = re.sub(r"^(beautiful|perfect|amazing|stunning|lovely|gorgeous)\s+", "", title, flags=re.I)
    words = cleaned.split()
    return " ".join(words[:12]).strip() or title

def generate_better_tags(listing):
    current = listing.get("tags") or []
    ideas = suggest_keywords(listing)
    needed = 13 - len(current)
    extras = [k for k in ideas if k not in current][:needed]
    return (current + extras)[:13]

def get_headers(api_key, access_token):
    return {"x-api-key": api_key, "Authorization": f"Bearer {access_token}", "Accept": "application/json"}

def fetch_listings(api_key, access_token, shop_id, state="active", limit=100):
    url = f"https://api.etsy.com/v3/application/shops/{shop_id}/listings"
    params = {"state": state, "limit": limit, "includes": "Images"}
    try:
        r = requests.get(url, headers=get_headers(api_key, access_token), params=params, timeout=30)
        if r.status_code == 200:
            return r.json().get("results", [])
        st.error(f"API {r.status_code}: {r.text[:300]}")
        return []
    except Exception as e:
        st.error(str(e))
        return []

def update_listing(api_key, access_token, shop_id, listing_id, **fields):
    url = f"https://api.etsy.com/v3/application/shops/{shop_id}/listings/{listing_id}"
    headers = get_headers(api_key, access_token)
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    data = {}
    if "title" in fields: data["title"] = fields["title"]
    if "description" in fields: data["description"] = fields["description"]
    if "tags" in fields:
        tags = fields["tags"]
        data["tags"] = ",".join(tags) if isinstance(tags, list) else tags
    try:
        r = requests.patch(url, headers=headers, data=data, timeout=30)
        return r.status_code in (200, 201), r.text
    except Exception as e:
        return False, str(e)

# ---------- Sidebar (collapsed by default on phone) ----------
with st.sidebar:
    st.header("Connection")
    demo_mode = st.toggle("Demo Mode", value=True)
    
    if not demo_mode:
        api_key = st.text_input("API Keystring", type="password")
        access_token = st.text_input("Access Token", type="password")
        shop_id = st.text_input("Shop ID")
        if st.button("Connect", type="primary"):
            if api_key and access_token and shop_id:
                with st.spinner("Loading..."):
                    listings = fetch_listings(api_key, access_token, shop_id)
                    st.session_state.listings = listings
                    st.session_state.connected = True
                    st.session_state.api_key = api_key
                    st.session_state.access_token = access_token
                    st.session_state.shop_id = shop_id
                    st.success(f"Loaded {len(listings)}")
            else:
                st.warning("Fill all fields")
    else:
        if st.button("Load Demo"):
            st.session_state.listings = copy.deepcopy(DEMO_LISTINGS)
            st.session_state.connected = True
            st.success("Demo loaded")

    st.caption("Open sidebar with the arrow / menu button")

# ---------- Main ----------
if "listings" not in st.session_state or not st.session_state.listings:
    st.info("Open the sidebar (☰ or arrow) and load Demo Mode to start.")
    st.markdown("""
    **What you can do**
    - See scores for every listing
    - Fix titles & tags
    - Review images
    - Check stock & price
    - Apply bulk suggestions
    """)
else:
    listings = st.session_state.listings
    analyses = []
    for l in listings:
        a = analyze_listing(l)
        a["listing_id"] = l["listing_id"]
        a["title"] = l.get("title", "")
        analyses.append(a)
    df = pd.DataFrame(analyses).sort_values("score")
    
    # Compact metrics (stack on mobile)
    st.subheader("Overview")
    if mobile:
        st.metric("Listings", len(listings))
        st.metric("Avg Score", f"{df['score'].mean():.0f}")
        st.metric("Need Work", int((df.score < 70).sum()))
        st.metric("Low Stock", int((df.quantity <= 3).sum()))
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Listings", len(listings))
        c2.metric("Avg Score", f"{df['score'].mean():.0f}")
        c3.metric("Need Work", int((df.score < 70).sum()))
        c4.metric("Low Stock", int((df.quantity <= 3).sum()))
    
    # Tabs still work well on phone
    tab1, tab2, tab3, tab4 = st.tabs(["Listings", "Fix One", "Bulk", "More"])
    
    with tab1:
        st.dataframe(
            df[["listing_id", "title", "score", "tag_count", "quantity", "price"]],
            use_container_width=True,
            hide_index=True,
            height=400,
            column_config={
                "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
                "price": st.column_config.NumberColumn("Price", format="$%.0f"),
                "title": st.column_config.TextColumn("Title", width="medium")
            }
        )
        csv = df.to_csv(index=False).encode()
        st.download_button("Download CSV", csv, "report.csv")
    
    with tab2:
        st.subheader("Fix a Listing")
        opts = {f"{l['listing_id']} — {l.get('title','')[:40]}": l for l in listings}
        sel_label = st.selectbox("Choose listing", list(opts.keys()))
        sel = opts[sel_label]
        a = analyze_listing(sel)
        
        st.metric("Score", f"{a['score']}/100")
        
        with st.expander("Issues & Suggestions", expanded=True):
            for i in a["issues"]:
                st.markdown(f"- {i}")
            for s in a["suggestions"]:
                st.markdown(f"- *{s}*")
        
        imgs = sel.get("images") or []
        if imgs:
            st.markdown("**Images**")
            for img in imgs[:3]:
                u = img.get("url_570xN") or img.get("url_fullxfull")
                if u:
                    st.image(u, use_container_width=True)
                if not img.get("alt_text"):
                    st.caption("⚠️ missing alt text")
        
        new_title = st.text_input("Title", value=sel.get("title", ""), max_chars=140)
        tags_str = st.text_area("Tags (comma separated)", value=", ".join(sel.get("tags", [])), height=100)
        new_desc = st.text_area("Description", value=sel.get("description", ""), height=150)
        new_tags = [t.strip() for t in tags_str.split(",") if t.strip()][:13]
        
        temp = copy.deepcopy(sel)
        temp.update({"title": new_title, "tags": new_tags, "description": new_desc})
        new_a = analyze_listing(temp)
        st.metric("New Score", f"{new_a['score']}/100", delta=new_a["score"] - a["score"])
        
        if st.button("Suggest Better Title & Tags"):
            st.session_state["sug_title"] = generate_better_title(sel)
            st.session_state["sug_tags"] = ", ".join(generate_better_tags(sel))
        
        if "sug_title" in st.session_state:
            st.success(st.session_state["sug_title"])
            st.info(st.session_state["sug_tags"])
        
        with st.expander("Keyword ideas"):
            st.write(", ".join(suggest_keywords(sel)))
        
        connected = st.session_state.get("connected") and not demo_mode
        if connected:
            if st.button("Push to Etsy", type="primary"):
                ok, msg = update_listing(
                    st.session_state.api_key, st.session_state.access_token,
                    st.session_state.shop_id, sel["listing_id"],
                    title=new_title, description=new_desc, tags=new_tags
                )
                st.success("Updated!") if ok else st.error(msg[:200])
        else:
            if st.button("Apply in Demo"):
                for l in st.session_state.listings:
                    if l["listing_id"] == sel["listing_id"]:
                        l["title"] = new_title
                        l["tags"] = new_tags
                        l["description"] = new_desc
                st.success("Applied (demo)")
                st.rerun()
    
    with tab3:
        st.subheader("Bulk Actions")
        choices = [f"{l['listing_id']} | {l.get('title','')[:35]}" for l in listings]
        selected = st.multiselect("Select listings", choices)
        action = st.selectbox("Action", ["Auto-fill tags", "Clean titles"])
        
        if st.button("Preview"):
            if selected:
                ids = [int(s.split("|")[0]) for s in selected]
                for l in listings:
                    if l["listing_id"] in ids:
                        if action == "Auto-fill tags":
                            st.write(f"**{l['listing_id']}**: {', '.join(generate_better_tags(l))}")
                        else:
                            st.write(f"**{l['listing_id']}**: {generate_better_title(l)}")
        
        if st.button("Apply in Demo"):
            if selected:
                ids = [int(s.split("|")[0]) for s in selected]
                for l in st.session_state.listings:
                    if l["listing_id"] in ids:
                        if action == "Auto-fill tags":
                            l["tags"] = generate_better_tags(l)
                        else:
                            l["title"] = generate_better_title(l)
                st.success("Applied")
                st.rerun()
    
    with tab4:
        st.subheader("Keywords")
        all_text = " ".join((l.get("title") or "") + " " + (l.get("description") or "") for l in listings)
        words = re.findall(r"\b[a-z]{4,}\b", all_text.lower())
        top = Counter(words).most_common(8)
        st.write("Frequent words: " + ", ".join(w for w, _ in top))
        st.write("Try: handmade gift, personalized gift, custom gift for her, unique home decor")
        
        st.subheader("Stock & Price")
        low = df[df.quantity <= 3]
        if len(low):
            st.warning(f"{len(low)} low/out of stock")
            st.dataframe(low[["listing_id", "title", "quantity", "price"]], use_container_width=True, hide_index=True)
        else:
            st.success("Stock looks good")

st.caption("Optimized for phone • Sidebar has connection options")
