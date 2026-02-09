document.addEventListener('DOMContentLoaded', () => {
    // Register ScrollTrigger
    gsap.registerPlugin(ScrollTrigger);

    // 1. Hero Parallax Effect
    const heroVideo = document.querySelector('.hero-video-container');
    const heroContent = document.querySelector('.hero-content');

    if (heroVideo) {
        gsap.to(heroVideo, {
            y: 100,
            scale: 1.05,
            scrollTrigger: {
                trigger: '#hero',
                start: 'top top',
                end: 'bottom top',
                scrub: true
            }
        });
    }

    if (heroContent) {
        gsap.to(heroContent, {
            y: -50,
            opacity: 0.8,
            scrollTrigger: {
                trigger: '#hero',
                start: 'top top',
                end: 'bottom top',
                scrub: true
            }
        });
    }

    // 2. Reveal Animations
    const reveals = document.querySelectorAll('.reveal:not(.reveal-alternate)');

    reveals.forEach((el) => {
        let x = 0;
        let y = 0;
        let scale = 1;

        if (el.classList.contains('reveal-up')) y = 40;
        if (el.classList.contains('reveal-down')) y = -40;
        if (el.classList.contains('reveal-left')) x = -40;
        if (el.classList.contains('reveal-right')) x = 40;
        if (el.classList.contains('reveal-scale')) scale = 0.95;

        gsap.fromTo(el,
            {
                opacity: 0,
                x: x,
                y: y,
                scale: scale
            },
            {
                opacity: 1,
                x: 0,
                y: 0,
                scale: 1,
                duration: 1.2,
                ease: "power2.out",
                scrollTrigger: {
                    trigger: el,
                    start: "top 85%", // Trigger when top of element is at 85% of viewport
                    toggleActions: "play none none none"
                }
            }
        );
    });

    // 2b. Alternating Reveals (One after another)
    const alternateContainers = document.querySelectorAll('.reveal-container');
    alternateContainers.forEach(container => {
        const items = container.querySelectorAll('.reveal-alternate');

        items.forEach((item, index) => {
            const isEven = index % 2 === 0;
            const startX = isEven ? -60 : 60;

            gsap.fromTo(item,
                {
                    opacity: 0,
                    x: startX
                },
                {
                    opacity: 1,
                    x: 0,
                    duration: 1.2,
                    delay: index * 0.2, // Continuous stagger
                    ease: "power2.out",
                    scrollTrigger: {
                        trigger: container,
                        start: "top 85%",
                        toggleActions: "play none none none"
                    }
                }
            );
        });
    });

    // 3. Stats Staggered Animation
    const statsCards = document.querySelectorAll('.stat-card');
    if (statsCards.length > 0) {
        gsap.fromTo(statsCards,
            {
                opacity: 0,
                y: 20
            },
            {
                opacity: 1,
                y: 0,
                duration: 0.8,
                stagger: 0.2,
                ease: "power2.out",
                scrollTrigger: {
                    trigger: ".research-stats",
                    start: "top 80%"
                }
            }
        );
    }
});
