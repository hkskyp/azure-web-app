
// 페이지 로드 완료 시 로딩 숨기기는 위에서 처리됨// 사이드바 및 네비게이션 관련 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const desktopMenuBtn = document.getElementById('desktopMenuBtn');
    const desktopHeader = document.getElementById('desktopHeader');
    const sidebarOverlay = document.getElementById('sidebarOverlay');

    // 사이드바 토글 함수
    function toggleSidebar() {
        sidebar.classList.toggle('collapsed');
        mainContent.classList.toggle('expanded');
        
        // 토글 버튼 아이콘 변경
        const isCollapsed = sidebar.classList.contains('collapsed');
        if (sidebarToggle) {
            sidebarToggle.textContent = '☰';
        }
        
        // 데스크톱 헤더 표시/숨김 (데스크톱에서만)
        if (window.innerWidth > 768) {
            if (isCollapsed) {
                desktopHeader.style.display = 'flex';
            } else {
                desktopHeader.style.display = 'none';
            }
        }
    }

    // 모바일 사이드바 열기
    function openMobileSidebar() {
        sidebar.classList.add('mobile-open');
        sidebarOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    // 모바일 사이드바 닫기
    function closeMobileSidebar() {
        sidebar.classList.remove('mobile-open');
        sidebarOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    // 이벤트 리스너
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', toggleSidebar);
    }

    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', openMobileSidebar);
    }

    if (desktopMenuBtn) {
        desktopMenuBtn.addEventListener('click', toggleSidebar);
    }

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', closeMobileSidebar);
    }

    // ESC 키로 모바일 사이드바 닫기
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeMobileSidebar();
        }
    });

    // 윈도우 리사이즈 시 모바일 사이드바 상태 정리
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            closeMobileSidebar();
            // 데스크톱에서 사이드바 상태에 따라 헤더 표시/숨김
            const isCollapsed = sidebar.classList.contains('collapsed');
            if (isCollapsed) {
                desktopHeader.style.display = 'flex';
            } else {
                desktopHeader.style.display = 'none';
            }
        } else {
            // 모바일에서는 데스크톱 헤더 숨김
            desktopHeader.style.display = 'none';
        }
    });

    // 네비게이션 링크 클릭 시 모바일에서 사이드바 닫기
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                closeMobileSidebar();
            }
        });
    });

    // 현재 페이지에 따른 사이드바 섹션 하이라이트
    const currentPath = window.location.pathname;
    const activeLink = document.querySelector(`.nav-link[href="${currentPath}"]`);
    
    if (activeLink) {
        // 활성 링크의 부모 섹션을 확장
        const parentSection = activeLink.closest('.nav-section');
        if (parentSection) {
            parentSection.classList.add('expanded');
        }
    }

    // 네비게이션 섹션 접기/펼치기 (선택사항)
    const sectionTitles = document.querySelectorAll('.nav-section-title');
    sectionTitles.forEach(title => {
        title.addEventListener('click', function() {
            const section = this.closest('.nav-section');
            section.classList.toggle('collapsed');
        });
    });
});

// 페이지 로딩 상태 표시 (선택사항)
function showPageLoading() {
    const loadingIndicator = document.createElement('div');
    loadingIndicator.className = 'page-loading';
    loadingIndicator.innerHTML = '<div class="loading-spinner"></div>';
    document.body.appendChild(loadingIndicator);
}

function hidePageLoading() {
    const loadingIndicator = document.querySelector('.page-loading');
    if (loadingIndicator) {
        loadingIndicator.remove();
    }
}

// 페이지 전환 시 로딩 표시
document.addEventListener('click', function(e) {
    const link = e.target.closest('a[href^="/"]');
    if (link && !link.target) {
        showPageLoading();
        // 실제 페이지 로드가 완료되면 hidePageLoading()이 호출됨
        setTimeout(hidePageLoading, 1000); // 백업 타이머
    }
});

    // 페이지 로드 시 초기 상태 설정
    window.addEventListener('load', function() {
        // 데스크톱에서 사이드바 상태 확인
        if (window.innerWidth > 768) {
            const isCollapsed = sidebar.classList.contains('collapsed');
            if (isCollapsed) {
                desktopHeader.style.display = 'flex';
            } else {
                desktopHeader.style.display = 'none';
            }
        }
    });