from . import instagram, tiktok, youtube

PUBLISHERS = {
    "instagram": instagram.publish,
    "tiktok": tiktok.publish,
    "youtube": youtube.publish,
}
