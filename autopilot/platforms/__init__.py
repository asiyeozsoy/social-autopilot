from . import facebook, instagram, tiktok, youtube

PUBLISHERS = {
    "instagram": instagram.publish,
    "facebook": facebook.publish,
    "tiktok": tiktok.publish,
    "youtube": youtube.publish,
}
