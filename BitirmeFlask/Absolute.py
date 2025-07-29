import os
import re
import time
from collections import defaultdict
import jellyfish
from Levenshtein import distance as levenshtein_distance
from googleapiclient.discovery import build
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

embed_model = SentenceTransformer("paraphrase-MiniLM-L6-v2")

def embed_text(text):
    return embed_model.encode(text)

# Gemini API'yi yapılandır
genai.configure(api_key="YOUR API KEY")
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-latest")

BASE_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "linkedin_kisiler")
API_KEY = "YOUR_API_KEY"
CSE_ID = "YOUR_CSE_ID"
LINKEDIN_EMAIL = "YOUR_EMAIL"
LINKEDIN_PASSWORD = "YOUR_PASSWORD"

KATEGORI_KELIMELERI = {
    "teknoloji": (
        "bilgisayar,yazılım,yapay zeka,veri bilimi,backend,full-stack,frontend,"
        "mobil,web,developer,geliştirici,programlama,devops,ai,ml,data,blockchain,"
        "nlp,python,cyber,siber güvenlik,siber,network,ağ,cloud,bulut,react,node,"
        "kotlin,flutter,angular,c#,java,javascript,django,rest api,api,microservices,"
        "linux,docker,kubernetes,postgre,mongodb,sql,ci/cd,agile,jira,scrum"
    ),
    "mühendislik": (
        "bilgisayar mühendisliği,yazılım mühendisliği,elektrik mühendisliği,"
        "elektronik,makine mühendisliği,inşaat mühendisliği,endüstri mühendisliği,"
        "uzay mühendisliği,mekatronik,jeoloji mühendisliği,metalürji,gemi mühendisliği,"
        "otomotiv mühendisliği,enerji mühendisliği,mühendis,ar-ge,test mühendisi,"
        "tasarım mühendisi,proses mühendisi,üretim mühendisi,çevre mühendisi"
    ),
    "sağlık": (
        "doktor,hemşire,fizyoterapist,eczacı,psikolog,cerrah,diyetisyen,intern,"
        "paramedik,acil tıp teknisyeni,psikiyatrist,klinik psikolog,aile hekimi,"
        "diş hekimi,ortodontist,radyolog,anestezi uzmanı,veteriner,sağlık yöneticisi,"
        "hastane,sağlık teknisyeni,obezite uzmanı,nörolog"
    ),
    "hukuk": (
        "avukat,hakim,savcı,hukuk danışmanı,noter,adalet,bilirkişi,hukuk müşaviri,"
        "hukukçu,icra memuru,ceza hukuku,borçlar hukuku,medeni hukuk,ticaret hukuku,"
        "avukatlık bürosu,baro,mahkeme,kanun,anlaşmazlık çözümü,uyuşmazlık çözümü,"
        "sözleşme hukuku,şirket avukatı"
    ),
    "iş dünyası": (
        "finans,muhasebe,girişimcilik,proje yönetimi,insan kaynakları,ürün yönetimi,"
        "ik,pazarlama,ceo,yönetici,finans asistanı,investment,investment officer,"
        "financial analyst,finans analisti,portföy yöneticisi,portfolio manager,"
        "cfo,strateji danışmanı,iş geliştirme,business development,crm,erp,raporlama,"
        "bütçe,denetim,reklam,satış müdürü,satış uzmanı,pazarlama müdürü,kpi,startup,"
        "venture capital,product manager,product owner,supply chain,tedarik zinciri"
    ),
    "tasarım": (
        "grafik tasarım,ux,ui,oyun tasarımı,mimarlık,moda tasarımı,endüstriyel tasarım,"
        "web tasarım,iç mimarlık,illustrator,photoshop,adobe,figma,canva,after effects,"
        "branding,logo,creative,art director,concept artist,animasyon,storyboard"
    ),
    "danışmanlık": (
        "it danışmanlığı,finansal danışmanlık,hukuk danışmanlığı,ik danışmanlığı,"
        "strateji danışmanlığı,yönetim danışmanlığı,veri danışmanı,crm danışmanı,"
        "danışman,consultant,freelance danışman,bağımsız danışman,business consultant,"
        "sap danışmanı,oracle danışmanı,dijital dönüşüm danışmanı"
    )
}



def generate_summary_with_gemini(profile_text):
    prompt = f"""
    Aşağıda bir kişinin LinkedIn profil bilgileri yer alıyor. Bu kişi hakkında üçüncü tekil şahısla yazılmış, konuşma diliyle yazılmış kısa bir tanıtım yazısı oluştur.

    Dil resmî olmasın ve övgü içermesin. "Ahmet şurada çalışmış, sonra şuraya geçmiş, şu anda da bunları yapmakta." gibi sade, sohbet havasında bir üslup kullan.

    Paragraf çok uzun olmasın ama kişiyi genel olarak tanıtsın. Ayrıca cümlenin içinde kişnin ismini kullanma. İşte profil bilgileri:

    {profile_text}
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini özetleme hatası: {str(e)}")
        return None


def google_search_advanced(name, city=None, job=None, uni=None, num=100):
    service = build("customsearch", "v1", developerKey=API_KEY)
    results = []
    start = 1
    query = f"{name} site:linkedin.com/in"
    if city:
        query += f" {city}"
    if job:
        query += f" {job}"
    if uni:
        query += f" {uni}"
    while len(results) < num:
        time.sleep(3)
        res = service.cse().list(q=query, cx=CSE_ID, start=start).execute()
        items = res.get("items", [])
        for item in items:
            link = item.get("link")
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            if "linkedin.com/in/" in link:
                name_score = name_similarity_score(name, title)
                boost = eslesme_puani(title, snippet, city, job, uni)
                final_score = max(0.0, min(1.0, name_score + boost))
                results.append((final_score, link, title, snippet))
                if len(results) >= num:
                    break
        start += 10
        if "nextPage" not in res.get("queries", {}):
            break
    results.sort(reverse=True, key=lambda x: x[0])
    return results[:num]


def name_similarity_score(input_name, found_title):
    title_name = re.split(r'[-|]', found_title)[0].strip()
    input_lower = input_name.lower()
    title_lower = title_name.lower()
    jaro = jellyfish.jaro_winkler_similarity(input_lower, title_lower)
    lev = 1 - (levenshtein_distance(input_lower, title_lower) / max(len(input_lower), len(title_lower), 1))
    return 0.7 * jaro + 0.3 * lev


def eslesme_puani(title, snippet, city=None, job=None, uni=None):
    combined = f"{title.lower()} {snippet.lower()}"
    boost = 0.0

    if city and city.lower() in combined:
        boost += 0.1

    if job:
        job_lower = job.lower()
        if job_lower in combined or job_lower.replace(' ', '-') in combined:
            boost += 0.2  # Meslek eşleşmesine daha fazla ağırlık veriyoruz

    if uni and uni.lower() in combined:
        boost += 0.1

    return min(boost, 0.3)


def linkedin_login():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)
    driver.get("https://www.linkedin.com/login")

    try:
        username = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "username")))
        password = driver.find_element(By.ID, "password")
        username.send_keys(LINKEDIN_EMAIL)
        password.send_keys(LINKEDIN_PASSWORD)
        password.submit()
        time.sleep(10)
        return driver
    except Exception as e:
        print(f"LinkedIn giriş hatası: {str(e)}")
        driver.quit()
        return None


def check_profile_contains_keywords(driver, keywords):
    """Profil sayfasında belirtilen anahtar kelimeleri arar"""
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        return all(keyword.lower() in body_text for keyword in keywords if keyword)
    except:
        return False


def extract_profile_sections(driver, profile_url, required_keywords=None):
    try:
        driver.get(profile_url)
        time.sleep(5)

        # Anahtar kelime kontrolü
        if required_keywords:
            if not check_profile_contains_keywords(driver, required_keywords):
                return "", None

        # Ana bölümü bulma
        main_section = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="profile-content"]/div/div[2]/div/div/main')))
        metin = main_section.text
        parsed_info = parse_linkedin_text(metin)
        return metin, parsed_info
    except Exception as e:
        print(f"[!] Profil alınamadı: {profile_url} -> {str(e)}")
        return "", []


def parse_linkedin_text(metin):
    bolum_etiketleri = {
        "Hakkında": "about",
        "Deneyim": "experience",
        "Eğitim": "education",
        "Yetenekler": "skills"
    }
    pattern = re.compile(r'^\s*(Hakkında|Deneyim|Eğitim|Yetenekler)\s*$', re.MULTILINE)
    basliklar = list(pattern.finditer(metin))
    bolumler = defaultdict(str)

    for i, match in enumerate(basliklar):
        baslik = match.group(1)
        start = match.end()
        end = basliklar[i + 1].start() if i + 1 < len(basliklar) else len(metin)
        icerik = metin[start:end].strip()
        if baslik in bolum_etiketleri:
            label = bolum_etiketleri[baslik]
            bolumler[label] += "\n" + icerik

    sonuc = []
    for label, text in bolumler.items():
        satirlar = [s.strip() for s in text.splitlines() if s.strip()]
        gorulen = set()
        benzersiz_satirlar = []
        for satir in satirlar:
            temiz = satir.strip()
            if not temiz or temiz in gorulen:
                continue
            if label == "about" and "faaliyet" in temiz.lower():
                break
            if label == "education" and (
                    temiz.lower().startswith("lisanslar ve sertifikalar") or
                    "eğitimin tümünü göster" in temiz.lower()
            ):
                break
            if label == "skills" and "yeteneğin tümünü göster" in temiz.lower():
                break
            benzersiz_satirlar.append(temiz)
            gorulen.add(temiz)
        if benzersiz_satirlar:
            sonuc.append({"label": label, "text": "\n".join(benzersiz_satirlar)})
    return sonuc if sonuc else None


def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def calculate_relevance_score(summary, kategori):
    keywords = [kw.strip().lower() for kw in KATEGORI_KELIMELERI.get(kategori, "").split(",") if kw.strip()]
    if not keywords:
        return 0.0

    summary_lower = summary.lower()

    # Anahtar kelime eşleşme oranı
    match_count = sum(1 for kw in keywords if kw in summary_lower)
    keyword_match_score = match_count / len(keywords)

    # SentenceTransformer vektör benzerliği
    kategori_embedding = embed_text(" ".join(keywords))
    summary_embedding = embed_text(summary)
    vector_score = cosine_similarity([summary_embedding], [kategori_embedding])[0][0]

    # Karma skor: %60 anahtar kelime eşleşmesi, %40 vektör benzerliği
    final_score = 0.6 * keyword_match_score + 0.4 * vector_score
    return float(round(final_score, 3))


def save_profile_data(profile_url, title, score, bilgiler):
    safe_title = sanitize_filename(title.strip())
    url_part = profile_url.split('/in/')[-1].split('?')[0]
    url_part = sanitize_filename(url_part)
    filename_base = f"{safe_title[:50]} [{url_part[:20]}] ({score:.2f})"
    json_path = os.path.join(BASE_DIR, filename_base + ".json")

    counter = 1
    original_json_path = json_path
    while os.path.exists(json_path):
        json_path = f"{original_json_path.rsplit('.', 1)[0]}_{counter}.json"
        counter += 1

    json_data = {
        "profile_url": profile_url,
        "score": round(score, 2),
        "title": title,
        "sections": bilgiler if bilgiler else []
    }

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)

    # Özet metni üret
    flat_text = ""
    for section in bilgiler:
        flat_text += f"\n\n## {section['label'].capitalize()}\n{section['text']}"
    summary = generate_summary_with_gemini(flat_text)

    # Özet txt dosyasını kaydet
    if summary:
        txt_path = os.path.join(BASE_DIR, filename_base + ".txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(summary)

    return json_path

def main():
    isim = input("Kimi aramak istiyorsun?: ").strip()
    hedef_kategori = input("Hedef kategori nedir? (örnek: teknoloji, hukuk, sağlık): ").strip().lower()
    city = input("Şehir bilgisi (boş bırakabilirsiniz): ").strip() or None
    job = input("Meslek bilgisi (boş bırakabilirsiniz): ").strip() or None
    uni = input("Üniversite bilgisi (boş bırakabilirsiniz): ").strip() or None

    print(f"\nAranıyor: {isim} {f'({city})' if city else ''} {f'({job})' if job else ''} {f'({uni})' if uni else ''}")

    profiller = google_search_advanced(isim, city, job, uni, num=20)
    if not profiller:
        print("Uygun profil bulunamadı.")
        return

    required_keywords = []
    if job:
        required_keywords.append(job)
    if city:
        required_keywords.append(city)

    filtered_profiles = [p for p in profiller if p[0] > 0.2]
    if not filtered_profiles:
        print("0.2 üzeri profil bulunamadı.")
        return

    driver = linkedin_login()
    if not driver:
        return

    en_iyi_profiller = []

    for idx, (score, profil_url, title, _) in enumerate(filtered_profiles, start=1):
        ham_text, bilgiler = extract_profile_sections(driver, profil_url, required_keywords)
        if not ham_text.strip() or bilgiler is None:
            continue

        # Profil metnini tek düz yazıya çevir
        flat_text = ""
        for section in bilgiler:
            flat_text += f"\n\n## {section['label'].capitalize()}\n{section['text']}"

        summary = generate_summary_with_gemini(flat_text)

        print(f"\n{title.strip()}\n")
        print(f"🔗 {profil_url}")

        if summary:
            print(f"📝 Özet:\n{summary}")
            #Kategori alaka skoru
            kategori_skoru = calculate_relevance_score(summary, hedef_kategori)
            print(f"📊 Alaka Skoru ({hedef_kategori}): {kategori_skoru:.3f}")

            en_iyi_profiller.append({
                "title": title.strip(),
                "url": profil_url,
                "summary": summary,
                "score": kategori_skoru
            })
        else:
            print("⚠️ Özet oluşturulamadı.")

        time.sleep(8 + idx % 3)

    driver.quit()

    # En yüksek 3 profili yazdır
    print("\n=== En İlgili 3 Profil ===")
    en_iyi_profiller.sort(key=lambda x: x["score"], reverse=True)
    for profil in en_iyi_profiller[:3]:
        print(
            f"\n{profil['title']}\n🔗 {profil['url']}\n📊 Skor: {profil['score']:.3f}\n📝 Özet:\n{profil['summary']}")

if __name__ == "__main__":
    main()
