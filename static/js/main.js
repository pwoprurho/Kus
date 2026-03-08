document.addEventListener('DOMContentLoaded', () => {

    // =================================================================
    // --- 2. MOBILE NAVIGATION TOGGLE ---
    // =================================================================
    const navToggles = document.querySelectorAll('.nav-toggle');
    const navList = document.getElementById('primary-navigation');

    if (navToggles.length > 0 && navList) {
        navToggles.forEach(toggle => {
            toggle.addEventListener('click', () => {
                const isVisible = navList.getAttribute('data-visible') === "true";
                const newState = (!isVisible).toString();

                // Toggle the data-visible attribute (Triggers CSS sliding)
                navList.setAttribute('data-visible', newState);

                // Toggle aria-expanded for accessibility on all toggles
                navToggles.forEach(t => {
                    t.setAttribute('aria-expanded', newState);
                    // Dynamic Icon Switching
                    const icon = t.querySelector('i');
                    if (icon) {
                        if (newState === "true") {
                            icon.classList.remove('fa-bars');
                            icon.classList.add('fa-times');
                        } else {
                            icon.classList.remove('fa-times');
                            icon.classList.add('fa-bars');
                        }
                    }
                });
            });
        });
    }
});