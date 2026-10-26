"""本站内容更新记录：例行抓取时间不算内容变化。"""
CONTENT_FIELDS = (
    "title", "description", "location", "startAt", "endAt", "eventDates",
    "applicationDeadline", "registrationStatus", "officialUrl", "imageUrl",
    "contentType", "releaseAt", "releaseLabel", "publishedAt", "priceLabel",
    "interestIds", "brand", "region", "sourceActive",
)


def content_changed(previous, current):
    return any(previous.get(key) != current.get(key) for key in CONTENT_FIELDS)


def with_update_times(previous, current, observed_at):
    if not observed_at:
        return current
    first_seen = previous.get("firstSeenAt") or previous.get("fetchedAt") or observed_at
    updated_at = previous.get("contentUpdatedAt") or first_seen
    if not previous or content_changed(previous, current):
        updated_at = observed_at
    return {**current, "firstSeenAt": first_seen, "contentUpdatedAt": updated_at}
