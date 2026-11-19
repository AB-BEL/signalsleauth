/**
 * Signal Sleuth — standard integration for uploaded chapter HTML games.
 *
 * Injected automatically when the server serves an uploaded game file.
 * Games MUST call SignalSleuthGame.submitScore() after each level evaluation
 * so scores reach MySQL (not only localStorage).
 *
 * Contract:
 *   await SignalSleuthGame.submitScore({
 *     level_num: 1,
 *     score: 25,
 *     max_score: 30,
 *     cleared: true,          // optional; server also derives from score/max >= 50%
 *     feedback: [             // optional; used in student PDF
 *       { question, answer, score, max, feedback }
 *     ]
 *   });
 *
 *   const data = await SignalSleuthGame.getMyScores();
 *   // data.levels = [{ level_num, best_score, max_score, attempts, cleared }, ...]
 */
(function (global) {
  "use strict";

  var CHAPTER = parseInt(global.SS_CHAPTER_NUM || "1", 10) || 1;
  var USER_ID = parseInt(global.SS_USER_ID || "0", 10) || 0;
  var API_BASE = (global.SS_API_BASE || "").replace(/\/$/, "");

  function url(path) {
    return API_BASE + path;
  }

  async function api(path, options) {
    options = options || {};
    var headers = Object.assign(
      { Accept: "application/json", "Content-Type": "application/json" },
      options.headers || {}
    );
    // Embedded in another origin (e.g. the mobile web app): cookies may be blocked,
    // so authenticate with the signed token the server injected into the page.
    if (global.SS_TOKEN && !headers.Authorization) {
      headers.Authorization = "Bearer " + global.SS_TOKEN;
    }
    var res = await fetch(url(path), {
      method: options.method || "GET",
      headers: headers,
      credentials: "same-origin",
      body: options.body != null ? JSON.stringify(options.body) : undefined,
    });
    var text = await res.text();
    var data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch (e) {
      throw new Error("Invalid API response (" + res.status + ")");
    }
    if (!res.ok || data.ok === false) {
      throw new Error(data.error || data.message || "HTTP " + res.status);
    }
    return data;
  }

  var SignalSleuthGame = {
    version: "1.0.0",
    chapterNum: CHAPTER,
    userId: USER_ID,

    /**
     * Submit one level attempt to the central backend.
     * Returns server result: { ok, level_cleared, attempts, total_score, ... }
     */
    submitScore: function (payload) {
      payload = payload || {};
      var body = {
        chapter_num: payload.chapter_num != null ? payload.chapter_num : CHAPTER,
        level_num: parseInt(payload.level_num, 10),
        // Preferred: answers for trusted server-side scoring
        answers: payload.answers || null,
        // Legacy fields ignored by server when answers are present
        feedback: payload.feedback || null,
      };
      if (!(body.level_num >= 1 && body.level_num <= 7)) {
        return Promise.reject(new Error("level_num must be 1–7"));
      }
      if (!body.answers || !body.answers.length) {
        return Promise.reject(new Error("answers[] required for server-side scoring"));
      }
      return api("/api/submit-score", { method: "POST", body: body });
    },

    /** Load this student's server-side scores for the current chapter. */
    getMyScores: function (chapterNum) {
      var ch = chapterNum != null ? chapterNum : CHAPTER;
      return api("/api/my-scores/" + ch);
    },

    /** Level lock / playable map from server. */
    getLevelStatus: function (chapterNum) {
      var ch = chapterNum != null ? chapterNum : CHAPTER;
      return api("/api/level-status/" + ch);
    },

    /** Convenience: overall pass rule used by the platform. */
    isLevelClearedByScore: function (score, maxScore) {
      maxScore = Number(maxScore) || 0;
      score = Number(score) || 0;
      return maxScore > 0 && score / maxScore >= 0.5;
    },
  };

  global.SignalSleuthGame = SignalSleuthGame;

  // Notify parent frame (optional dashboards listening for updates)
  try {
    if (global.parent && global.parent !== global) {
      global.parent.postMessage(
        { type: "ss-bridge-ready", chapter: CHAPTER, version: SignalSleuthGame.version },
        "*"
      );
    }
  } catch (e) {}
})(typeof window !== "undefined" ? window : this);
