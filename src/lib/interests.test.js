import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { matchesTopic, matchesAudience, contentLabel } from "./interests.js";

const { topics } = JSON.parse(readFileSync(new URL("../data/interests.json", import.meta.url)));

test("REBORN aliases enter her view without being assigned to boyfriend", () => {
  const item = { title: "家庭教師ヒットマンREBORN! POP UP" };
  assert.equal(matchesAudience(item, "mine", topics), true);
  assert.equal(matchesAudience(item, "boyfriend", topics), false);
});

test("Splatoon merchandise belongs to both boyfriend topics", () => {
  const item = { interestIds: ["splatoon", "game_merch"], contentType: "collab" };
  assert.equal(matchesTopic(item, "splatoon", topics), true);
  assert.equal(matchesAudience(item, "boyfriend", topics), true);
  assert.equal(matchesAudience(item, "mine", topics), false);
  assert.equal(contentLabel(item), "联名资讯");
});

test("generic cosmetics are not automatically preferred brand lipstick", () => {
  assert.equal(matchesTopic({ title: "FAS 护肤体验活动" }, "lipstick", topics), false);
  assert.equal(matchesTopic({ interestIds: ["lipstick"] }, "lipstick", topics), true);
  assert.equal(contentLabel({}), "线下活动");
});
