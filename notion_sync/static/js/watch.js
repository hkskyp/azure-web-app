(function () {
    var config = window.__WATCH_CONFIG;
    var video = document.getElementById("videoPlayer");
    var progressBar = document.getElementById("progressBar");
    var progressText = document.getElementById("progressText");
    var completeBtn = document.getElementById("completeBtn");

    // 비디오 소스 비동기 로딩 — 페이지 렌더 후 영상 로드
    if (config.streamUrl) {
        video.src = config.streamUrl;
        video.preload = "metadata";
    }

    if (config.previewMode) {
        if (completeBtn) completeBtn.style.display = 'none';
        return;
    }

    var intervalId = null;
    var completed = config.isCompleted;
    var currentProgress = config.progress;
    var sessionStartTime = new Date().toISOString();

    // 물리적 시청 시간 추적 (이전 누적값부터 시작)
    var accumulatedSeconds = config.watchedSeconds;
    var playStartTime = null;

    updateButtonState();

    video.addEventListener("loadedmetadata", function () {
        if (config.currentPosition > 0) {
            video.currentTime = config.currentPosition;
        }
    });

    video.addEventListener("play", function () {
        playStartTime = Date.now();
        startInterval();
    });

    video.addEventListener("pause", function () {
        flushPlayTime();
        stopInterval();
    });

    video.addEventListener("ended", function () {
        flushPlayTime();
        stopInterval();
    });

    video.addEventListener("timeupdate", function () {
        if (video.duration > 0) {
            currentProgress = Math.min(100, (video.currentTime / video.duration) * 100);
            updateProgressUI(currentProgress);
            updateButtonState();
        }
    });

    function flushPlayTime() {
        if (playStartTime) {
            accumulatedSeconds += (Date.now() - playStartTime) / 1000;
            playStartTime = null;
        }
    }

    function getTotalWatched() {
        var total = accumulatedSeconds;
        if (playStartTime) total += (Date.now() - playStartTime) / 1000;
        return total;
    }

    function getSessionWatched() {
        return getTotalWatched() - config.watchedSeconds;
    }

    // --- 공통 데이터 빌더 ---

    function buildProgressData() {
        return {
            page_id: config.pageId,
            current_position: video.currentTime,
            duration: video.duration,
            watched_seconds: getTotalWatched(),
        };
    }

    function buildSessionData() {
        return {
            page_id: config.pageId,
            current_position: video.currentTime,
            duration: video.duration,
            watched_seconds: getTotalWatched(),
            session_watched_seconds: getSessionWatched(),
            session_start: sessionStartTime,
        };
    }

    // --- 전송 ---

    function startInterval() {
        stopInterval();
        intervalId = setInterval(sendProgress, 30000);
    }

    function stopInterval() {
        if (intervalId) { clearInterval(intervalId); intervalId = null; }
    }

    function sendProgress() {
        fetch("/api/webhook/tracking/progress", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(buildProgressData()),
        })
            .then(function (r) { return r.json(); })
            .then(function (res) {
                if (res.progress !== undefined) {
                    currentProgress = res.progress;
                    updateProgressUI(res.progress);
                    updateButtonState();
                }
            })
            .catch(function () {});
    }

    function sendComplete() {
        flushPlayTime();
        completed = true;
        completeBtn.disabled = true;
        completeBtn.textContent = "완료됨";

        fetch("/api/webhook/tracking/complete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(buildProgressData()),
        })
            .then(function (r) { return r.json(); })
            .then(function (res) {
                if (res.progress !== undefined) {
                    currentProgress = res.progress;
                    updateProgressUI(res.progress);
                }
            })
            .catch(function () {});

        fetch("/api/webhook/tracking/session-end", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(buildSessionData()),
        }).catch(function () {});
    }

    // --- UI ---

    function updateProgressUI(progress) {
        var p = Math.min(100, Math.max(0, progress));
        progressBar.style.width = p.toFixed(1) + "%";
        progressText.textContent = p.toFixed(1) + "%";
    }

    function updateButtonState() {
        if (completed) {
            completeBtn.disabled = true;
            completeBtn.textContent = "완료됨";
        } else if (currentProgress >= 95) {
            completeBtn.disabled = false;
        } else {
            completeBtn.disabled = true;
        }
    }

    completeBtn.addEventListener("click", function () {
        if (completed || currentProgress < 95) return;
        if (confirm("수강을 완료하시겠습니까?")) {
            sendComplete();
        }
    });

    // --- 페이지 이탈 ---

    var exitSent = false;
    function sendBeaconOnExit() {
        if (exitSent || !video.duration) return;
        exitSent = true;
        flushPlayTime();
        navigator.sendBeacon("/api/webhook/tracking/complete", JSON.stringify(buildProgressData()));
        navigator.sendBeacon("/api/webhook/tracking/session-end", JSON.stringify(buildSessionData()));
    }

    window.addEventListener("pagehide", sendBeaconOnExit);
    window.addEventListener("beforeunload", sendBeaconOnExit);
})();
