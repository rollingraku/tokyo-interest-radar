import { useEffect, useMemo, useState } from "react";
import "./App.css";
import eventData from "./data/events.json";
import updateStatus from "./data/update_status.json";
import interestConfig from "./data/interests.json";
import { matchesTopic, matchesAudience, contentLabel, newestFirst } from "./lib/interests";

const categories = [
  { id: "all", label: "全部", icon: "✦" },
  { id: "game", label: "游戏", icon: "🎮" },
  { id: "anime", label: "动漫", icon: "🌸" },
  { id: "beauty", label: "美妆", icon: "💄" },
  { id: "fashion", label: "服装", icon: "👗" },
];

const events = eventData.filter(
  (event) => ["verified", "sourced"].includes(event.status) && event.sourceActive !== false
);

const STORAGE_KEY = "tokyo-interest-radar-favorites";

function readFavorites() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(saved)
      ? saved.filter((id) => typeof id === "string")
      : [];
  } catch {
    return [];
  }
}

function formatDate(value) {
  if (!value) return "待确认";

  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return "待确认";

  const [, year, month, day] = match;
  const date = new Date(`${value}T00:00:00`);

  if (
    Number.isNaN(date.getTime()) ||
    date.getFullYear() !== Number(year) ||
    date.getMonth() + 1 !== Number(month) ||
    date.getDate() !== Number(day)
  ) {
    return "待确认";
  }

  return `${Number(month)}月${Number(day)}日`;
}

function formatPeriod(startAt, endAt) {
  if (!startAt) return "待确认";
  if (!endAt || endAt === startAt) return formatDate(startAt);
  return `${formatDate(startAt)} — ${formatDate(endAt)}`;
}

function formatRegistration(event) {
  if (event.applicationDeadline) {
    return formatDate(event.applicationDeadline);
  }

  const labels = {
    ticket_required: "需购票 / 查看官方",
    partial_reservation: "部分需预约",
    varies: "按具体活动确认",
    not_required: "无需报名",
    unknown: "待确认",
  };

  return labels[event.registrationStatus] || "待确认";
}

function itemDate(event) {
  if (event.contentType === "news" || event.contentType === "collab") {
    return event.publishedAt ? `${event.historical ? "历史公告" : "资讯发布"} · ${event.publishedAt.replaceAll("-", "/")}` : "资讯日期待确认";
  }
  if (event.contentType === "product") return event.releaseAt ? formatDate(event.releaseAt) : event.releaseLabel || "发售日待公布";
  return event.eventDates?.length > 1 ? "多个举办日 · 见下方" : formatPeriod(event.startAt, event.endAt);
}

function EventCover({ event, children }) {
  const [failedUrl, setFailedUrl] = useState(null);
  const hasImage = event.imageUrl && failedUrl !== event.imageUrl;

  return (
    <div className={`card-cover ${hasImage ? "has-image" : ""} ${hasImage && event.imageKind === "franchise_art" ? "has-reference" : ""}`}>
      {hasImage ? (
        <>
          <img
            className="cover-image"
            src={event.imageUrl?.startsWith("/")
              ? `${import.meta.env.BASE_URL}${event.imageUrl.slice(1)}`
              : event.imageUrl}
            alt={event.imageAlt || `${event.title} 官方封面`}
            loading="lazy"
            decoding="async"
            onError={() => setFailedUrl(event.imageUrl)}
          />
          <a
            className="cover-source"
            href={event.imageSourceUrl || event.officialUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            {event.imageKind === "franchise_art" ? "作品插画 · 非商品图 ↗" : "官方图片 ↗"}
          </a>
        </>
      ) : (
        <>
          <span className="cover-top">TOKYO / {event.category.toUpperCase()}</span>
          <span className="cover-mark" aria-hidden="true">✳</span>
          <strong className="cover-title">{event.title}</strong>
          <span className="cover-bottom">{event.tag} · TOKYO RADAR 精选</span>
        </>
      )}
      <span className="cover-date">{itemDate(event)}</span>
      {children}
    </div>
  );
}

function App() {
  const [category, setCategory] = useState("all");
  const [audience, setAudience] = useState("all");
  const [topic, setTopic] = useState("all");
  const [contentType, setContentType] = useState("all");
  const [view, setView] = useState("all");
  const [keyword, setKeyword] = useState("");
  const [favorites, setFavorites] = useState(() => {
  const savedFavorites = readFavorites();

  const validIds = new Set(events.map((event) => event.id));

  return savedFavorites.filter((id) => validIds.has(id));
});

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites));
    } catch {
      // 如果浏览器禁止存储，当前页面仍可正常收藏。
    }
  }, [favorites]);

  const visibleEvents = useMemo(() => {
    const query = keyword.trim().toLocaleLowerCase();

    return newestFirst(events.filter((event) => {
      const categoryMatch =
        category === "all" || event.category === category;

      const favoriteMatch =
        view === "all" || favorites.includes(event.id);

      const searchText = [
        event.title,
        event.description,
        event.location,
        event.tag, event.brand, event.releaseLabel,
        ...(event.interestIds || []).map((id) => interestConfig.topics.find((entry) => entry.id === id)?.label || id),
      ]
        .join(" ")
        .toLocaleLowerCase();

      return categoryMatch && favoriteMatch && searchText.includes(query)
        && matchesAudience(event, audience, interestConfig.topics)
        && (topic === "all" || matchesTopic(event, topic, interestConfig.topics))
        && (contentType === "all" || (event.contentType || "event") === contentType);
    }));
  }, [category, view, keyword, favorites, audience, topic, contentType]);

  function toggleFavorite(id) {
    setFavorites((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id]
    );
  }

  function resetFilters() {
    setCategory("all");
    setAudience("all");
    setTopic("all");
    setContentType("all");
    setKeyword("");
    setView("all");
  }

  return (
    <div className="app">
      <header className="site-header">
        <div className="header-inner">
          <a className="brand" href="#" aria-label="Tokyo Interest Radar 首页">
            <span className="brand-symbol">✳</span>
            <span>tokyo<span className="brand-light">radar.</span></span>
          </a>

          <span className="header-caption">YOUR CITY, YOUR INTERESTS.</span>
        </div>
      </header>

      <main>
        <section className="hero">
          <div className="hero-inner">
            <div className="hero-copy">
              <span className="eyebrow">
                <span className="eyebrow-dot" />
                DISCOVER WHAT'S NEXT IN TOKYO
              </span>

              <h1>
                发现东京，
                <br />
                <span>让心动发生。</span>
              </h1>

              <p className="hero-description">
                从游戏联动到限定美妆，从动漫展览到时尚快闪。
                <br className="desktop-break" />
                收藏每一个让你心动的城市灵感。
              </p>

              <div className="hero-actions">
                <a href="#discover" className="primary-button">
                  探索活动 <span aria-hidden="true">↗</span>
                </a>
                <span className="hero-note">CURATED FOR THE CURIOUS</span>
              </div>
            </div>

            <div className="hero-art" aria-hidden="true">
              <div className="art-orbit orbit-one" />
              <div className="art-orbit orbit-two" />
              <div className="art-center">
                <span className="art-star">✳</span>
                <span className="art-text">TOKYO<br />IS YOURS</span>
              </div>
              <span className="floating-icon icon-one">✿</span>
              <span className="floating-icon icon-two">✦</span>
              <span className="floating-icon icon-three">♡</span>
              <span className="art-coordinate">35° 40′ N / 139° 41′ E</span>
            </div>
          </div>
        </section>

        <section className="discovery-section" id="discover">
          <div className="section-heading">
            <div>
              <span className="section-kicker">THE DISCOVERY EDIT</span>
              <h2>今天想发现什么？</h2>
              <p>跟着兴趣出发，发现城市里的新鲜事。</p>
              <p className="update-note">
                最近同步：{new Date(updateStatus.lastSuccessfulAt).toLocaleString("zh-CN", {
                  timeZone: "Asia/Tokyo", month: "numeric", day: "numeric",
                  hour: "2-digit", minute: "2-digit", hour12: false,
                })}（东京时间）
                {updateStatus.sources && ` · ${updateStatus.successfulSourceCount}/${updateStatus.attemptedSourceCount} 个官网同步成功`}
                {updateStatus.status === "partial" && " · 部分来源暂未更新，已保留旧信息"}
              </p>
              <div className="source-list" aria-label="活动数据来源">
                {Object.entries(updateStatus.sources || {}).map(([key, source]) => (
                  <a key={key} href={source.sourceUrl} target="_blank" rel="noopener noreferrer"
                    title={source.lastSuccessfulAt ? `最近成功：${new Date(source.lastSuccessfulAt).toLocaleString("zh-CN", { timeZone: "Asia/Tokyo" })}` : "尚未成功同步"}>
                    {source.sourceName} · {source.status === "failed" ? "暂未更新" : `${source.eventCount} 条`}
                    {source.warnings?.length > 0 && `（${source.warnings.length} 篇待确认）`}
                  </a>
                ))}
              </div>
            </div>

            <span className="demo-label">✳ OFFICIAL SOURCES · 官方来源</span>
          </div>

          <section className="interest-hub" aria-label="我们关注的内容">
            <div className="interest-heading">
              <div><span className="section-kicker">OUR LITTLE RADAR</span><h3>两个人的兴趣雷达</h3></div>
              <span className="interest-region">日本发售优先 · 东京及周边活动</span>
            </div>
            <div className="audience-tabs" aria-label="兴趣视角">
              {[{ id: "all", label: "我们一起看" }, { id: "mine", label: "我关注的" }, { id: "boyfriend", label: "男朋友关注的" }].map((entry) => (
                <button type="button" key={entry.id} aria-pressed={audience === entry.id}
                  onClick={() => { setAudience(entry.id); setTopic("all"); setCategory("all"); }}>
                  {entry.label}
                </button>
              ))}
            </div>
            <div className="topic-grid">
              {interestConfig.topics.filter((entry) => audience === "all" || entry.owner === audience).map((entry) => (
                <button type="button" key={entry.id} className={`topic-card ${topic === entry.id ? "active" : ""}`}
                  aria-pressed={topic === entry.id}
                  onClick={() => { setTopic(topic === entry.id ? "all" : entry.id); setCategory("all"); }}>
                  <span className="topic-icon" aria-hidden="true">{entry.icon}</span>
                  <strong>{entry.label}</strong><small>{entry.description}</small>
                  <span className="topic-count">{events.filter((item) => matchesTopic(item, entry.id, interestConfig.topics)).length} 条内容 ↗</span>
                </button>
              ))}
            </div>
            <details className="interest-channels">
              <summary>关注的官方渠道 · 查看接入情况</summary>
              <div className="channel-grid">
                {interestConfig.sources.filter((source) => topic === "all" || source.topics.includes(topic)).map((source) => {
                  const report = updateStatus.sources?.[source.sourceKey];
                  return <a key={source.label} href={source.url} target="_blank" rel="noopener noreferrer">
                    <strong>{source.label} ↗</strong>
                    <span>{source.mode === "link" ? "仅官网入口" : report?.status === "success" ? "已自动同步" : "自动同步暂不可用"}</span>
                    <small>{source.note}</small>
                  </a>;
                })}
              </div>
            </details>
          </section>

          <div className="content-type-tabs" aria-label="内容类型">
            {[{ id: "all", label: "全部类型" }, { id: "event", label: "线下活动" }, { id: "product", label: "新品 / 周边" }, { id: "news", label: "官方资讯" }, { id: "collab", label: "联名资讯" }].map((entry) => (
              <button key={entry.id} type="button" aria-pressed={contentType === entry.id} onClick={() => setContentType(entry.id)}>{entry.label}</button>
            ))}
          </div>

          <div className="toolbar">
            <div className="category-list" aria-label="活动分类">
              {categories.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`category-button ${
                    category === item.id ? "active" : ""
                  }`}
                  onClick={() => setCategory(item.id)}
                  aria-pressed={category === item.id}
                >
                  <span>{item.icon}</span>
                  {item.label}
                </button>
              ))}
            </div>

            <label className="search-box">
              <span aria-hidden="true">⌕</span>
              <input
                type="search"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="搜索作品、品牌、周边、地点..."
                aria-label="搜索活动或地点"
              />
            </label>
          </div>

          <div className="result-header">
            <div className="view-tabs" aria-label="活动视图">
              <button
                type="button"
                className={view === "all" ? "selected" : ""}
                onClick={() => setView("all")}
                aria-pressed={view === "all"}
              >
                全部内容
              </button>

              <button
                type="button"
                className={view === "favorites" ? "selected" : ""}
                onClick={() => setView("favorites")}
                aria-pressed={view === "favorites"}
              >
                ♡ 我的收藏
                <span className="favorite-count">{favorites.length}</span>
              </button>
            </div>

            <span className="result-count">
              最新更新优先 · {visibleEvents.length} 条
            </span>
          </div>

          {visibleEvents.length > 0 ? (
            <div className="event-grid">
              {visibleEvents.map((event) => {
                const isFavorite = favorites.includes(event.id);
                const categoryInfo = categories.find(
                  (item) => item.id === event.category
                );

                return (
                  <article
                    className={`event-card theme-${event.category}`}
                    key={event.id}
                  >
                    <EventCover event={event}>
                      <button
                        type="button"
                        className={`favorite-button ${
                          isFavorite ? "is-favorite" : ""
                        }`}
                        onClick={() => toggleFavorite(event.id)}
                        aria-label={
                          isFavorite
                            ? `取消收藏：${event.title}`
                            : `收藏：${event.title}`
                        }
                        aria-pressed={isFavorite}
                      >
                        {isFavorite ? "♥" : "♡"}
                      </button>
                    </EventCover>

                    <div className="card-content">
                      <div className="card-tags">
                        <span className="category-tag">
                          {categoryInfo?.icon} {categoryInfo?.label} · {contentLabel(event)}
                        </span>
                        <span className="sample-tag">
                      {event.status === "sourced" ? "官网自动同步" : "人工核实记录"}
                      </span>
                      </div>

                      <h3>{event.title}</h3>
                      <p className="card-description">{event.description}</p>
                      <p className="card-source">来源：{event.sourceName}</p>

                      <div className="event-details">
                        <div className="detail-row">
                          <span>{event.contentType ? "⌖ 地区 / 渠道" : "⌖ 地点"}</span>
                          <strong>{event.location || "待确认"}</strong>
                        </div>
                        <div className="detail-row">
                          <span>{event.contentType === "product" ? "▦ 发售时间" : event.contentType ? "▦ 资讯发布" : "▦ 举办日期"}</span>
                          <strong>
                            {event.contentType ? itemDate(event) : event.eventDates?.length > 0
                              ? event.eventDates.map(formatDate).join("、")
                              : formatPeriod(event.startAt, event.endAt)}
                          </strong>
                        </div>
                        <div className="detail-row">
                          <span>{event.contentType === "product" ? "◷ 价格" : event.contentType ? "◷ 信息说明" : "◷ 报名信息"}</span>
                          <strong>{event.contentType === "product" ? event.priceLabel || "以官方为准" : event.contentType ? "发售与参与条件以原文为准" : formatRegistration(event)}</strong>
                        </div>
                      </div>

                      {event.officialUrl ? (
                        <a
                          className="official-link"
                          href={event.officialUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          查看官方详情 <span>↗</span>
                        </a>
                      ) : (
                        <span className="official-link unavailable">
                          官方链接待确认 <span>—</span>
                        </span>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <div className="empty-state">
              <span className="empty-icon">✳</span>
              <h3>这里暂时还没有发现</h3>
              <p>
                {view === "favorites"
                  ? "还没有符合条件的收藏活动，试着收藏几张喜欢的卡片吧。"
                  : "没有找到符合条件的活动，试试其他分类或关键词。"}
              </p>
              <button type="button" onClick={resetFilters}>
                查看全部内容 ↗
              </button>
            </div>
          )}
        </section>

        <section className="bottom-banner">
          <span className="banner-decoration">✳</span>
          <div>
            <span className="section-kicker">A LITTLE MORE EVERY DAY</span>
            <h2>生活不止于日常。</h2>
            <p>下一次心动，也许就在东京的某个转角。</p>
          </div>
          <span className="banner-decoration">✦</span>
        </section>
      </main>

      <footer className="site-footer">
        <span>✳ tokyo radar.</span>
        <span>MADE FOR CURIOUS MINDS · MVP v0.1</span>
        <span>活动信息以官方最新公告为准</span>
      </footer>
    </div>
  );
}

export default App;
