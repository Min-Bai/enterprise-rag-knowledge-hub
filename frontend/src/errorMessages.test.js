import assert from "node:assert/strict";
import test from "node:test";

import { getUserErrorMessage } from "./errorMessages.js";


test("document upload rate limit is presented in Chinese with retry time", () => {
  assert.equal(
    getUserErrorMessage({
      code: "DOCUMENT_UPLOAD_RATE_LIMITED",
      retryAfterSeconds: 125,
    }),
    "上传操作过于频繁，请在3 分钟后重试。",
  );
});


test("unknown API errors use a Chinese fallback", () => {
  assert.equal(
    getUserErrorMessage({ status: 418 }),
    "操作失败，请稍后重试。",
  );
});
