"use strict";

var assert = require("node:assert/strict");
var test = require("node:test");
var progress = require("./static/js/skill_learning_progress.js");

test("progress status handles not started, partial, completed, and empty topics", function () {
    assert.equal(progress.getProgressStatus(0, 5), "not_started");
    assert.equal(progress.getProgressStatus(2, 5), "in_progress");
    assert.equal(progress.getProgressStatus(5, 5), "completed");
    assert.equal(progress.getProgressStatus(6, 5), "completed");
    assert.equal(progress.getProgressStatus(0, 0), "not_started");
});

test("topic action switches to reset only when all materials are complete", function () {
    assert.equal(progress.getTopicAction(0, 4), "complete");
    assert.equal(progress.getTopicAction(2, 4), "complete");
    assert.equal(progress.getTopicAction(4, 4), "reset");
    assert.equal(progress.getTopicAction(0, 0), "complete");
});

test("progress filters combine status and beneficiary search", function () {
    var beneficiaries = [
        { name: "Ava", searchText: "ava santos", status: "not_started" },
        { name: "Ben", searchText: "ben cruz", status: "in_progress" },
        { name: "Bea", searchText: "bea cruz", status: "completed" }
    ];

    assert.deepEqual(
        progress.filterProgress(beneficiaries, "all", " cruz").map(function (item) { return item.name; }),
        ["Ben", "Bea"]
    );
    assert.deepEqual(
        progress.filterProgress(beneficiaries, "completed", "").map(function (item) { return item.name; }),
        ["Bea"]
    );
    assert.deepEqual(
        progress.filterProgress(beneficiaries, "in_progress", "bea"),
        []
    );
});

test("topic status filtering uses the same state rules", function () {
    var topics = [
        { searchText: "Reading", completed: 0, total: 4, status: progress.getProgressStatus(0, 4) },
        { searchText: "Gardening", completed: 2, total: 3, status: progress.getProgressStatus(2, 3) },
        { searchText: "Planning", completed: 3, total: 3, status: progress.getProgressStatus(3, 3) }
    ];

    assert.deepEqual(
        progress.filterProgress(topics, "in_progress", "").map(function (item) { return item.searchText; }),
        ["Gardening"]
    );
    assert.deepEqual(
        progress.filterProgress(topics, "all", "READ").map(function (item) { return item.searchText; }),
        ["Reading"]
    );
});

test("single-material updates send beneficiary and material IDs with either action", function () {
    assert.deepEqual(
        progress.buildMaterialProgressPayload(48, "material-a", true),
        {
            beneficiary_id: "48",
            material_id: "material-a",
            action: "complete"
        }
    );
    assert.deepEqual(
        progress.buildMaterialProgressPayload(48, "material-a", false),
        {
            beneficiary_id: "48",
            material_id: "material-a",
            action: "uncomplete"
        }
    );
});

test("progress response parser accepts the normalized single and topic response shape", async function () {
    var singleResult = await progress.parseProgressUpdateResponse({
        ok: true,
        status: 200,
        json: function () {
            return Promise.resolve({ ok: true, completed: true, updated: 1, total: 1 });
        }
    }, true);
    var topicResult = await progress.parseProgressUpdateResponse({
        ok: true,
        status: 200,
        json: function () {
            return Promise.resolve({ ok: true, completed: false, updated: 4, total: 4 });
        }
    }, false);

    assert.equal(singleResult.updated, 1);
    assert.equal(topicResult.updated, 4);
    await assert.rejects(
        progress.parseProgressUpdateResponse({
            ok: false,
            status: 404,
            json: function () {
                return Promise.resolve({ error: "Material not found." });
            }
        }, true),
        /Material not found/
    );
});
