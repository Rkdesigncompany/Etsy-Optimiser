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

if st.button("📱 Open / Share on phone", type="primary"):
    st.info("Bookmark this page on your phone: tap the browser menu → Add to Home screen")
    st.code("https://rfupfuxmsc5gjtxx4cvv.streamlit.app", language=None)
    st.caption("Or copy the link above and open it in your phone browser")

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
    cleaned = re.sub(r"^(beautiful|perfect|amazing|stunning|lovely|gorgeous|funny|rude)\s+", "", title, flags=re.I)
    words = [w for w in cleaned.split() if w.lower() not in ["the", "a", "an", "for", "with"]]
    return " ".join(words[:12]).strip() or title

def generate_better_description(listing):
    title = (listing.get("title") or "This item").strip()
    desc = (listing.get("description") or "").strip()
    
    # Aggressive clean of promo / RebelsKage / handmade
    patterns = [
        r"(?i).*?rebelskage.*?\n?",
        r"(?i).*?promo\s*code.*?\n?",
        r"(?i).*?use\s*code.*?\n?",
        r"(?i).*?\d+%\s*(off|discount).*?\n?",
        r"(?i).*?discount.*?checkout.*?\n?",
        r"(?i)\bhand[- ]?made\b",
        r"(?i)\bhandmade\b",
    ]
    for p in patterns:
        desc = re.sub(p, "", desc)
    desc = re.sub(r"\n{3,}", "\n\n", desc).strip()
    desc = re.sub(r"^\s*[\)\*\-\•]+\s*", "", desc, flags=re.M).strip()
    
    materials = ", ".join(listing.get("materials") or [])
    base = desc if len(desc) > 40 else title
    extra = ""
    if materials:
        extra += f"\n\nMaterials: {materials}."
    extra += "\n\nGreat as a gift or for personal use. High quality."
    return (base + extra).strip()[:5000]

def generate_alt_text(listing, rank=1):
    title = (listing.get("title") or "Product").strip()
    # Short clean alt text from title
    alt = re.sub(r"[^a-zA-Z0-9\s]", " ", title)
    alt = " ".join(alt.split()[:8])
    return f"{alt} product photo {rank}"[:250]

def update_shipping_price(api_key, access_token, shop_id, shipping_profile_id, destination_id, primary_cost, shared_secret=None):
    url = f"https://api.etsy.com/v3/application/shops/{shop_id}/shipping-profiles/{shipping_profile_id}/destinations/{destination_id}"
    headers = get_headers(api_key, access_token, shared_secret)
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    data = {"primary_cost": primary_cost}
    try:
        r = requests.put(url, headers=headers, data=data, timeout=30)
        return r.status_code in (200, 201), r.text
    except Exception as e:
        return False, str(e)
    # Etsy requires re-associating via upload endpoint for alt text
    url = f"https://api.etsy.com/v3/application/shops/{shop_id}/listings/{listing_id}/images"
    headers = get_headers(api_key, access_token, shared_secret)
    data = {
        "listing_image_id": listing_image_id,
        "alt_text": alt_text,
        "overwrite": "true"
    }
    try:
        r = requests.post(url, headers=headers, data=data, timeout=30)
        return r.status_code in (200, 201), r.text
    except Exception as e:
        return False, str(e)
    current = listing.get("tags") or []
    ideas = suggest_keywords(listing)
    needed = 13 - len(current)
    extras = [k for k in ideas if k not in current][:needed]
    return (current + extras)[:13]

def get_headers(api_key, access_token, shared_secret=None):
    key = f"{api_key}:{shared_secret}" if shared_secret else api_key
    return {"x-api-key": key, "Authorization": f"Bearer {access_token}", "Accept": "application/json"}

def fetch_listings(api_key, access_token, shop_id, shared_secret=None, state="active", limit=100):
    url = f"https://api.etsy.com/v3/application/shops/{shop_id}/listings"
    params = {"state": state, "limit": limit, "includes": "Images"}
    try:
        r = requests.get(url, headers=get_headers(api_key, access_token, shared_secret), params=params, timeout=30)
        if r.status_code == 200:
            return r.json().get("results", [])
        st.error(f"API {r.status_code}: {r.text[:300]}")
        return []
    except Exception as e:
        st.error(str(e))
        return []

def update_listing(api_key, access_token, shop_id, listing_id, shared_secret=None, **fields):
    url = f"https://api.etsy.com/v3/application/shops/{shop_id}/listings/{listing_id}"
    headers = get_headers(api_key, access_token, shared_secret)
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
        shared_secret = st.text_input("Shared Secret", type="password")
        access_token = st.text_input("Access Token", type="password")
        shop_id = st.text_input("Shop ID")
        if st.button("Connect", type="primary"):
            if api_key and access_token and shop_id:
                with st.spinner("Loading..."):
                    listings = fetch_listings(api_key, access_token, shop_id, shared_secret)
                    st.session_state.listings = listings
                    st.session_state.connected = True
                    st.session_state.api_key = api_key
                    st.session_state.shared_secret = shared_secret
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
                    st.session_state.get("shared_secret"),
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
        action = st.selectbox("Action", ["Auto-fill tags", "Clean titles", "Improve descriptions", "Titles + Descriptions", "Add alt text"])
        
        if st.button("Preview"):
            if selected:
                ids = [int(s.split("|")[0]) for s in selected]
                for l in listings:
                    if l["listing_id"] in ids:
                        if action == "Auto-fill tags":
                            st.write(f"**{l['listing_id']}**: {', '.join(generate_better_tags(l))}")
                        elif action == "Clean titles":
                            st.write(f"**{l['listing_id']}**: {generate_better_title(l)}")
                        elif action == "Add alt text":
                            imgs = l.get("images") or []
                            alts = [generate_alt_text(l, i+1) for i in range(len(imgs))]
                            st.write(f"**{l['listing_id']}**: {alts}")
                        else:
                            st.write(f"**{l['listing_id']} Title:** {generate_better_title(l)}")
                            st.write(f"**Desc:** {generate_better_description(l)[:150]}...")
        
        if st.button("Apply", type="primary"):
            if selected and st.session_state.get("connected") and not st.session_state.get("demo"):
                ids = [int(s.split("|")[0]) for s in selected]
                progress = st.progress(0)
                for i, l in enumerate(st.session_state.listings):
                    if l["listing_id"] in ids:
                        if action == "Add alt text":
                            imgs = l.get("images") or []
                            for idx, img in enumerate(imgs):
                                if not img.get("alt_text"):
                                    alt = generate_alt_text(l, idx+1)
                                    img_id = img.get("listing_image_id")
                                    if img_id:
                                        ok, msg = update_image_alt(
                                            st.session_state.api_key, st.session_state.access_token,
                                            st.session_state.shop_id, l["listing_id"],
                                            img_id, alt, st.session_state.get("shared_secret")
                                        )
                                        if ok:
                                            img["alt_text"] = alt
                                        else:
                                            st.warning(f"{l['listing_id']} img {idx+1}: {str(msg)[:60]}")
                            continue
                        updates = {}
                        if action in ("Clean titles", "Titles + Descriptions"):
                            updates["title"] = generate_better_title(l)
                        if action in ("Improve descriptions", "Titles + Descriptions"):
                            updates["description"] = generate_better_description(l)
                        if action == "Auto-fill tags":
                            updates["tags"] = generate_better_tags(l)
                        if updates:
                            ok, msg = update_listing(
                                st.session_state.api_key, st.session_state.access_token,
                                st.session_state.shop_id, l["listing_id"],
                                st.session_state.get("shared_secret"),
                                **updates
                            )
                            if ok:
                                l.update(updates)
                            else:
                                st.error(f"{l['listing_id']}: {str(msg)[:80]}")
                    progress.progress((i+1)/len(st.session_state.listings))
                st.success("Done")
                st.rerun()
            else:
                st.info("Connect your real shop first")
    
    with tab4:
        st.subheader("Profit Calculator")
        st.caption("Based on your real Etsy fees (UK)")
        vat_registered = st.checkbox("I am VAT registered (reclaim VAT on costs)", value=False)
        col1, col2 = st.columns(2)
        with col1:
            sell_price = st.number_input("Sell price (£)", value=11.99, min_value=0.0, step=0.5)
            pod_cost = st.number_input("Gelato product cost (£)", value=6.20, min_value=0.0, step=0.1)
        with col2:
            ship_charged = st.number_input("Shipping you charge buyer (£)", value=2.50, min_value=0.0, step=0.5)
            ship_cost = st.number_input("Your actual shipping cost (£)", value=0.0, min_value=0.0, step=0.5)
        
        order_total = sell_price + ship_charged
        transaction_fee = order_total * 0.065
        processing_fee = order_total * 0.04 + 0.20
        regulatory_fee = order_total * 0.0048
        fees_before_vat = transaction_fee + processing_fee + regulatory_fee + 0.20
        vat_on_fees = fees_before_vat * 0.20
        total_fees = fees_before_vat + vat_on_fees
        
        cost_base = pod_cost + ship_cost
        # If VAT registered, reclaim the 20% so use ex-VAT cost
        if vat_registered:
            total_cost = cost_base / 1.20
        else:
            total_cost = cost_base * 1.20
        
        profit = order_total - total_cost - total_fees
        margin = (profit / order_total * 100) if order_total else 0
        
        st.metric("Estimated profit", f"£{profit:.2f}")
        st.metric("Margin", f"{margin:.1f}%")
        status = "VAT reclaimed" if vat_registered else "VAT not reclaimed"
        st.write(f"{status}  |  Etsy fees: £{total_fees:.2f}  |  Your costs: £{total_cost:.2f}")

        st.subheader("Image & Mockup Check")
        low_img = [l for l in listings if len(l.get("images") or []) < 5]
        if low_img:
            st.warning(f"{len(low_img)} listings have fewer than 5 images")
            for l in low_img[:8]:
                st.write(f"**{l['listing_id']}**: {l.get('title','')[:50]}")
                prompt = f"Professional product mockup of {l.get('title','product')}, white background, studio lighting, e-commerce style, high resolution"
                st.caption(prompt)
        else:
            st.success("Most listings have enough images")

        st.subheader("Bulk Price Adjust")
        pct = st.slider("Change selected prices by %", -20, 30, 0)
        if st.button("Preview price changes") and pct != 0:
            st.write(f"Example: £11.99 → £{11.99 * (1 + pct/100):.2f}")
            st.info("Select listings in Bulk tab first. Live updates coming next.")

        st.subheader("Refresh Reminder")
        st.write("Older listings can get a small visibility boost from a minor title or tag edit.")
        st.caption("Use Bulk → Clean titles on listings that have been up a while.")
        issues = []
        for l in listings:
            imgs = l.get("images") or []
            if len(imgs) < 3:
                issues.append({"id": l["listing_id"], "issue": "Few images", "detail": len(imgs)})
            if not any(i.get("alt_text") for i in imgs):
                issues.append({"id": l["listing_id"], "issue": "Missing alt text", "detail": ""})
            if len(l.get("description") or "") < 200:
                issues.append({"id": l["listing_id"], "issue": "Short description", "detail": len(l.get("description") or "")})
            if len(l.get("tags") or []) < 10:
                issues.append({"id": l["listing_id"], "issue": "Low tags", "detail": len(l.get("tags") or [])})
        if issues:
            st.dataframe(pd.DataFrame(issues), use_container_width=True, hide_index=True)
        else:
            st.success("All listings look healthy")

        st.subheader("Price Ideas")
        prices = [p for p in df["price"] if p > 0]
        if prices:
            avg = sum(prices) / len(prices)
            st.metric("Average price", f"£{avg:.2f}")
            under = df[df.price < avg * 0.8]
            if len(under):
                st.write(f"{len(under)} listings priced under 80% of average — consider raising")
                st.dataframe(under[["listing_id", "title", "price"]], use_container_width=True, hide_index=True)

        st.subheader("Stock Alerts")
        low = df[df.quantity <= 3]
        if len(low):
            st.warning(f"{len(low)} low or out of stock")
            st.dataframe(low[["listing_id", "title", "quantity", "price"]], use_container_width=True, hide_index=True)
        else:
            st.success("Stock looks good")

        st.subheader("Keywords")
        all_text = " ".join((l.get("title") or "") + " " + (l.get("description") or "") for l in listings)
        words = re.findall(r"\b[a-z]{4,}\b", all_text.lower())
        top = Counter(words).most_common(10)
        st.write("Top words: " + ", ".join(w for w, _ in top))

        st.subheader("Export")
        csv = df.to_csv(index=False).encode()
        st.download_button("Download full CSV", csv, "etsy_listings.csv")

        st.subheader("Bulk Shipping Price")
        new_ship = st.number_input("New primary shipping price (£)", value=2.50, min_value=0.0, step=0.5)
        if st.button("Apply shipping price", type="primary"):
            if selected and st.session_state.get("connected") and not st.session_state.get("demo"):
                ids = [int(s.split("|")[0]) for s in selected]
                progress = st.progress(0)
                for i, l in enumerate(st.session_state.listings):
                    if l["listing_id"] in ids:
                        # Get shipping info
                        ship_url = f"https://api.etsy.com/v3/application/listings/batch/shipping?listing_ids={l['listing_id']}"
                        try:
                            r = requests.get(ship_url, headers=get_headers(st.session_state.api_key, st.session_state.access_token, st.session_state.get("shared_secret")), timeout=30)
                            if r.status_code == 200:
                                data = r.json()
                                results = data.get("results", [])
                                if results and results[0].get("shipping_profile"):
                                    profile = results[0]["shipping_profile"]
                                    pid = profile.get("shipping_profile_id")
                                    dests = profile.get("shipping_profile_destinations", [])
                                    if dests:
                                        dest_id = dests[0].get("shipping_profile_destination_id")
                                        ok, msg = update_shipping_price(
                                            st.session_state.api_key, st.session_state.access_token,
                                            st.session_state.shop_id, pid, dest_id, new_ship,
                                            st.session_state.get("shared_secret")
                                        )
                                        if ok:
                                            st.success(f"Updated shipping on {l['listing_id']}")
                                        else:
                                            st.warning(f"{l['listing_id']}: {str(msg)[:80]}")
                                    else:
                                        st.warning(f"{l['listing_id']}: no destination found")
                                else:
                                    st.warning(f"{l['listing_id']}: no shipping profile")
                            else:
                                st.warning(f"{l['listing_id']}: could not fetch shipping")
                        except Exception as e:
                            st.warning(str(e)[:80])
                    progress.progress((i+1)/len(st.session_state.listings))
                st.success("Shipping update finished")
            else:
                st.info("Connect your shop and select listings first")

st.caption("Optimized for phone • Sidebar has connection options")
