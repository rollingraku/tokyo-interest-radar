export function matchesTopic(item, topic, topics) {
  if (item.interestIds?.includes(topic)) return true;
  const config = topics.find((entry) => entry.id === topic);
  const text = [item.title, item.description, item.tag].join(" ").toLowerCase();
  return Boolean(config?.keywords?.some((word) => text.includes(word.toLowerCase())));
}

export function matchesAudience(item, audience, topics) {
  return audience === "all" || topics.some(
    (topic) => topic.owner === audience && matchesTopic(item, topic.id, topics),
  );
}

export function contentLabel(item) {
  return { product: "新品 / 周边", news: "官方资讯", collab: "联名资讯" }[item.contentType] || "线下活动";
}

export function newestFirst(items) {
  const timestamp = (item) => {
    for (const value of [item.contentUpdatedAt, item.firstSeenAt, item.publishedAt, item.lastVerifiedAt]) {
      const parsed = value ? Date.parse(value) : NaN;
      if (Number.isFinite(parsed)) return parsed;
    }
    return 0;
  };
  return [...items].sort((a, b) => timestamp(b) - timestamp(a));
}

export function migrateFavorites(saved, items) {
  const ids = new Map();
  for (const item of items) {
    ids.set(item.id, item.id);
    for (const previousId of item.legacyIds || []) ids.set(previousId, item.id);
  }
  return [...new Set(saved.map((id) => ids.get(id)).filter(Boolean))];
}
