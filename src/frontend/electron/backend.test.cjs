const test = require("node:test");
const assert = require("node:assert/strict");

const { isChitrikaHealth } = require("./backend.cjs");

test("authenticated launcher handshake validates Chitrika identity", () => {
  assert.equal(
    isChitrikaHealth(JSON.stringify({ service: "chitrika", ready: true })),
    true,
  );
  assert.equal(isChitrikaHealth(JSON.stringify({ status: "ok" })), false);
  assert.equal(isChitrikaHealth("not-json"), false);
});
