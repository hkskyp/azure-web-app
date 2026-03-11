(function () {
    var config = window.__WATCH_CONFIG;
    var video = document.getElementById("videoPlayer");
    var progressBar = document.getElementById("progressBar");
    var progressText = document.getElementById("progressText");
    var completeBtn = document.getElementById("completeBtn");

    var intervalId = null;
    var completed = config.isCompleted;
    var currentProgress = config.progress;

    // 물리적 시청 시간 추적
    var accumulatedSeconds = config.watchedSeconds;
    var playStartTime = null;

    // 초기 버튼 상태
    updateButtonState();

    // 이어보기: 이전 재생 위치 복원
    video.addEventListener("loadedmetadata", function () {
        if (config.currentPosition > 0) {
            video.currentTime = config.currentPosition;
        }
    });

    // 재생 시작/재개
    video.addEventListener("play", function () {
        playStartTime = Date.now();
        startInterval();
    });

    // 일시정지
    video.addEventListener("pause", function () {
        flushPlayTime();
        stopInterval();
    });

    // 영상 종료
    video.addEventListener("ended", function () {
        flushPlayTime();
        stopInterval();
    });

    // 재생 위치 변화 시 진도율 실시간 반영
    video.addEventListener("timeupdate", function () {
        if (video.duration > 0) {
            var localProgress = Math.min(100, Math.max(0, (video.currentTime / video.duration) * 100));
            currentProgress = localProgress;
            updateProgressUI(currentProgress);
            updateButtonState();
        }
    });

    // 현재 재생 세션의 물리 시간을 누적
    function flushPlayTime() {
        if (playStartTime) {
            accumulatedSeconds += (Date.now() - playStartTime) / 1000;
            playStartTime = null;
        }
    }

    // 현재까지 총 물리 시청 시간 (초)
    function getTotalWatched() {
        var total = accumulatedSeconds;
        if (playStartTime) {
            total += (Date.now() - playStartTime) / 1000;
        }
        return total;
    }

    // 30초 간격 진행률 전송
    function startInterval() {
        stopInterval();
        intervalId = setInterval(sendProgress, 30000);
    }

    function stopInterval() {
        if (intervalId) {
            clearInterval(intervalId);
            intervalId = null;
        }
    }

    function sendProgress() {
        var data = {
            page_id: config.pageId,
            current_position: video.currentTime,
            duration: video.duration,
            watched_seconds: getTotalWatched(),
        };
        fetch("/api/tracking/progress", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
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

        var data = {
            page_id: config.pageId,
            current_position: video.currentTime,
            duration: video.duration,
            watched_seconds: getTotalWatched(),
        };
        fetch("/api/tracking/complete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        })
            .then(function (r) { return r.json(); })
            .then(function (res) {
                if (res.progress !== undefined) {
                    currentProgress = res.progress;
                    updateProgressUI(res.progress);
                }
            })
            .catch(function () {});
    }

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

    // 수강 완료 버튼 — 95% 이상일 때만, confirm 후 처리
    completeBtn.addEventListener("click", function () {
        if (completed || currentProgress < 95) return;
        if (confirm("수강을 완료하시겠습니까?")) {
            sendComplete();
        }
    });

    // 페이지 이탈 시 sendBeacon
    function sendBeaconProgress() {
        if (!video.duration) return;
        flushPlayTime();
        var data = JSON.stringify({
            page_id: config.pageId,
            current_position: video.currentTime,
            duration: video.duration,
            watched_seconds: getTotalWatched(),
        });
        navigator.sendBeacon("/api/tracking/progress", data);
    }

    window.addEventListener("pagehide", sendBeaconProgress);
    window.addEventListener("beforeunload", sendBeaconProgress);
})();
