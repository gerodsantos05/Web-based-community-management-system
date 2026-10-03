(function () {
  "use strict";

  var DEFAULT_CFG = {
    type: "line",
    options: {
      responsive: true,
      maintainAspectRatio: false,
      elements: {
        line: { tension: 0.35, borderWidth: 2 },
        point: { radius: 0 }
      },
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false }
      },
      scales: {
        x: { display: false, grid: { display: false } },
        y: { display: false, grid: { display: false }, beginAtZero: true }
      },
      animation: { duration: 1600, easing: "easeInOutCubic" }
    }
  };

  function createSparkline(canvas, data, stroke, fill) {
    if (!canvas || typeof Chart === "undefined") {
      return null;
    }

    var ctx = canvas.getContext("2d");
    var cfg = JSON.parse(JSON.stringify(DEFAULT_CFG));
    cfg.data = {
      labels: data.map(function (_, i) { return i + 1; }),
      datasets: [{
        data: data,
        borderColor: stroke || "rgba(16,185,129,1)",
        backgroundColor: fill || "rgba(16,185,129,0.12)",
        fill: !!fill
      }]
    };

    if (canvas.__sparkInstance) {
      try {
        canvas.__sparkInstance.destroy();
      } catch (_) {}
    }

    canvas.__sparkInstance = new Chart(ctx, cfg);
    return canvas.__sparkInstance;
  }

  function parseDataAttr(canvas) {
    var json = canvas.getAttribute("data-spark");
    if (json) {
      try {
        return JSON.parse(json);
      } catch (e) {}
    }

    var csv = canvas.getAttribute("data-series");
    if (csv) {
      return csv.split(",").map(function (s) {
        return Number(s.trim()) || 0;
      });
    }

    return [];
  }

  window.sparklineHelpers = {
    createSparkline: createSparkline,
    triggerKpiSparklineAnimations: function (root) {
      var scope = root && root.querySelectorAll ? root : document;
      var nodes = scope.querySelectorAll(".kpi-sparkline canvas");
      nodes.forEach(function (canvas) {
        var data = parseDataAttr(canvas);
        if (!data || !data.length) {
          data = [0, 0, 0, 0, 0, 0, 0];
        }

        var stroke = canvas.getAttribute("data-stroke") || "rgba(16,185,129,1)";
        var fill = canvas.getAttribute("data-fill") || "rgba(16,185,129,0.12)";
        createSparkline(canvas, data, stroke, fill);
      });
    }
  };

  function init() {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", function () {
        window.sparklineHelpers.triggerKpiSparklineAnimations();
      });
    } else {
      window.sparklineHelpers.triggerKpiSparklineAnimations();
    }

    window.addEventListener("load", function () {
      window.sparklineHelpers.triggerKpiSparklineAnimations();
    });
  }

  init();
})();
