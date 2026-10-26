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
