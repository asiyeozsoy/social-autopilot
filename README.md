# social-autopilot

Factyeap ve TinyNotesForU için otomatik paylaşım. Her saat GitHub üzerinde çalışır, zamanı gelen içerikleri Instagram, TikTok ve YouTube'a açıklamalarıyla yükler. Bilgisayarın açık olması gerekmez.

## Nasıl çalışır

```
content/
  tinynotes/2026-11-02_1500_monday/
    post.yaml        ← ne zaman, hangi platforma, hangi açıklamayla
    instagram.png
    tiktok.png
  factyeap/2026-11-03_1800_honey/
    post.yaml
    video.mp4
state/published.json ← neyin ne zaman yüklendiğinin kaydı (program yazar)
```

1. Claude her hafta içerikleri ve `post.yaml` dosyalarını `content/` klasörüne ekler.
2. `pages.yml` görselleri herkese açık bir adrese koyar (Instagram ve TikTok görseli oradan çeker).
3. `publish.yml` her saat başı +17. dakikada çalışır ve zamanı gelen postları yükler.
4. Her yükleme `state/published.json` dosyasına yazılır; aynı post iki kez yüklenmez.
5. Hata olursa bir sonraki saat tekrar dener (en fazla 3 kez). 6 saatten fazla geciken post atlanır, böylece bir aksaklıktan sonra bir haftalık içerik aynı anda yüklenmez.

### post.yaml örneği

```yaml
brand: factyeap                      # factyeap | tinynotes
publish_at: 2026-11-03T18:00:00+01:00 # Üsküp saati (kış: +01:00, yaz: +02:00)
platforms:
  instagram: {kind: reel,  media: [video.mp4], caption: "..."}
  tiktok:    {kind: video, media: [video.mp4], caption: "..."}
  youtube:   {kind: short, media: [video.mp4], title: "...", description: "..."}
```

Instagram: `image`, `carousel` (2–10 görsel), `reel` · TikTok: `photo` (kaydırmalı da olur), `video` · YouTube: `short` (sadece video).

## Platform sınırları

- **YouTube:** API yalnızca video yükleyebilir. Görsel (Topluluk) gönderileri otomatik yüklenemez.
- **TikTok:** TikTok uygulamamızı incelemeden (audit) önce yüklenen her şey **yalnızca sana görünür** olur. İnceleme geçince `TIKTOK_PRIVACY` değişkeni `PUBLIC_TO_EVERYONE` yapılır.
- **Instagram:** Hesap Profesyonel olmalı ve bir Facebook sayfasına bağlı olmalı.
- **AI etiketi:** YouTube ve TikTok videolarında "yapay zekâ ile üretildi" bildirimi otomatik açılır.

## Kurulum (bir kez)

Gizli anahtarları (token) **sadece sen** GitHub'a girersin; kimseyle, Claude dahil, paylaşma.

### 1. Depo ve medya adresi
1. GitHub'da **public** bir depo aç: `social-autopilot` (ücretsiz GitHub Pages için public olmalı; anahtarlar ayrı ve gizli saklanır).
2. Settings → Pages → Source: **GitHub Actions**.
3. Settings → Secrets and variables → Actions → **Variables**:
   - `MEDIA_BASE_URL` = `https://<kullanıcı-adın>.github.io/social-autopilot`
   - `ENABLED_PLATFORMS` = `instagram` (ilk test için; diğerleri hazır oldukça `instagram,tiktok,youtube`)

### 2. Instagram (her marka için)
1. Instagram uygulaması → Ayarlar → Hesap türü → **Profesyonel hesaba geç** (Creator).
2. Bir Facebook sayfası aç (Factyeap, TinyNotesForU) ve Instagram hesabını sayfaya bağla.
3. developers.facebook.com → My Apps → **Create App** (tür: Business) → "Instagram" ürününü ekle.
4. Graph API Explorer'da sayfan için izin ver: `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`.
5. Uzun ömürlü **sayfa** token'ını ve Instagram işletme hesap ID'sini al.
6. GitHub **Secrets**: `TINYNOTES_IG_TOKEN`, `TINYNOTES_IG_USER_ID` (Factyeap için `FACTYEAP_...`).

### 3. YouTube
1. console.cloud.google.com → yeni proje → **YouTube Data API v3**'ü etkinleştir.
2. OAuth izin ekranı: External, kapsam `youtube.upload`, durumu **In production** yap (Testing modunda token 7 günde ölür).
3. OAuth Client (Desktop) oluştur → `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` secret'ları.
4. Her kanal için bir kez izin ver, çıkan refresh token'ı `TINYNOTES_YT_REFRESH_TOKEN` / `FACTYEAP_YT_REFRESH_TOKEN` olarak kaydet.
5. Kota: günde yaklaşık 6 video yükleme.

### 4. TikTok
1. developers.tiktok.com → uygulama oluştur → **Content Posting API** + **Direct Post** ekle, `video.publish` izni iste.
2. `MEDIA_BASE_URL` adresini uygulamada **URL prefix** olarak doğrula (foto postlar için şart).
3. `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET` secret'ları; her hesap için izin verip `..._TT_REFRESH_TOKEN`.
4. Uygulamayı incelemeye (audit) gönder. Geçene kadar postlar gizli yüklenir.

### 5. Test
Actions → **Publish due posts** → Run workflow → `dry_run` işaretli. Log'da "would publish ..." satırlarını gör. Sonra işareti kaldırıp gerçek çalıştır.

## Yerel komutlar

```bash
pip install -r requirements.txt
python -m autopilot.main --check          # kuyruğu doğrula, sıradakileri listele
python -m autopilot.main --dry-run        # neyin yükleneceğini göster, hiçbir şey yükleme
python -m pytest -q tests                 # testler (internet gerekmez)
tools/watermark.sh factyeap brand/ <videolar> <çıkış>   # videolara logo bas
```
