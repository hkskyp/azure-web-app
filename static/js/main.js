// 상단 네비게이션 및 모바일 메뉴 관련 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const header = document.getElementById('header');
    const mobileToggle = document.getElementById('mobileToggle');
    const mobileMenu = document.getElementById('mobileMenu');
    const mobileOverlay = document.getElementById('mobileOverlay');
    const mobileClose = document.getElementById('mobileClose');

    // 헤더 스크롤 효과
    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 10) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    });

    // 모바일 메뉴 열기
    function openMobileMenu() {
        mobileMenu.classList.add('active');
        mobileOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';

        // 햄버거 아이콘을 X로 변경
        mobileToggle.classList.add('active');
    }

    // 모바일 메뉴 닫기
    function closeMobileMenu() {
        mobileMenu.classList.remove('active');
        mobileOverlay.classList.remove('active');
        document.body.style.overflow = '';

        // X 아이콘을 햄버거로 변경
        mobileToggle.classList.remove('active');
    }

    // 이벤트 리스너
    if (mobileToggle) {
        mobileToggle.addEventListener('click', function() {
            if (mobileMenu.classList.contains('active')) {
                closeMobileMenu();
            } else {
                openMobileMenu();
            }
        });
    }

    if (mobileClose) {
        mobileClose.addEventListener('click', closeMobileMenu);
    }

    if (mobileOverlay) {
        mobileOverlay.addEventListener('click', closeMobileMenu);
    }

    // ESC 키로 모바일 메뉴 닫기
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeMobileMenu();
        }
    });

    // 윈도우 리사이즈 시 모바일 메뉴 상태 정리
    window.addEventListener('resize', function() {
        if (window.innerWidth > 992) {
            closeMobileMenu();
        }
    });

    // 모바일 메뉴 내 링크 클릭 시 메뉴 닫기
    const mobileLinks = document.querySelectorAll('.mobile-sub-list a');
    mobileLinks.forEach(link => {
        link.addEventListener('click', closeMobileMenu);
    });

    // 부드러운 스크롤 (앵커 링크용)
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId !== '#') {
                e.preventDefault();
                const target = document.querySelector(targetId);
                if (target) {
                    const headerHeight = header.offsetHeight;
                    const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - headerHeight;
                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });
                }
            }
        });
    });
});

// ===== 스크롤 애니메이션 (Intersection Observer) =====
document.addEventListener('DOMContentLoaded', function() {
    // 애니메이션 대상 요소들
    const animateElements = document.querySelectorAll('.scroll-animate, .section-header, .card');

    // Intersection Observer 설정
    const observerOptions = {
        root: null,
        rootMargin: '0px 0px -50px 0px',
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                // 한 번 애니메이션 후 관찰 중지 (성능 최적화)
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // 각 요소 관찰 시작
    animateElements.forEach(el => {
        observer.observe(el);
    });

    // 카드에 순차 딜레이 추가
    const cardGrids = document.querySelectorAll('.card-grid');
    cardGrids.forEach(grid => {
        const cards = grid.querySelectorAll('.card');
        cards.forEach((card, index) => {
            card.classList.add('scroll-animate');
            card.classList.add(`delay-${(index % 4) + 1}`);
        });
    });
});
