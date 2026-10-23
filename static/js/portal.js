/* Minimal portal interactions; no legacy template plugins are required. */
(function () {
    var slideshow = document.getElementById('heroSlideshow');
    if (slideshow) {
        var slides = slideshow.querySelectorAll('.hero-slide');
        var pagination = slideshow.querySelector('.hero-pagination');
        var dots = slideshow.querySelectorAll('.hero-dot');
        var motion = window.matchMedia('(prefers-reduced-motion: reduce)');
        var current = 0;
        var timer;

        function showSlide(index) {
            slides[current].classList.remove('active');
            slides[current].setAttribute('aria-hidden', 'true');
            dots[current].removeAttribute('aria-current');
            current = index;
            slides[current].classList.add('active');
            slides[current].removeAttribute('aria-hidden');
            dots[current].setAttribute('aria-current', 'true');
        }

        function startSlideshow() {
            window.clearInterval(timer);
            if (!motion.matches && !document.hidden) {
                timer = window.setInterval(function () {
                    showSlide((current + 1) % slides.length);
                }, 5000);
            }
        }

        if (slides.length > 1 && dots.length === slides.length && pagination) {
            pagination.hidden = false;
            dots.forEach(function (dot, index) {
                dot.addEventListener('click', function () {
                    showSlide(index);
                    startSlideshow();
                });
            });
            motion.addEventListener('change', startSlideshow);
            document.addEventListener('visibilitychange', startSlideshow);
            startSlideshow();
        }
    }

    document.querySelectorAll('.preloader').forEach(function (element) { element.remove(); });
    var toggles = document.querySelectorAll('[data-toggle="dropdown"]');
    function closeDropdowns(except) {
        toggles.forEach(function (button) {
            if (button === except) return;
            button.setAttribute('aria-expanded', 'false');
            var parent = button.closest('.dropdown');
            if (parent) {
                parent.classList.remove('show');
                var menu = parent.querySelector('.dropdown-menu');
                if (menu) menu.classList.remove('show');
            }
        });
    }
    toggles.forEach(function (button) {
        button.setAttribute('aria-expanded', 'false');
        button.addEventListener('click', function (event) {
            event.preventDefault();
            var parent = button.closest('.dropdown');
            if (!parent) return;
            var open = !parent.classList.contains('show');
            closeDropdowns(button);
            parent.classList.toggle('show', open);
            var menu = parent.querySelector('.dropdown-menu');
            if (menu) menu.classList.toggle('show', open);
            button.setAttribute('aria-expanded', String(open));
        });
        button.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') { closeDropdowns(); button.focus(); }
        });
    });
    document.addEventListener('click', function (event) {
        if (!event.target.closest('.dropdown')) closeDropdowns();
    });
    document.querySelectorAll('[data-digits-only]').forEach(function (input) {
        input.addEventListener('input', function () {
            input.value = input.value.replace(/[^0-9]/g, '').slice(0, 10);
        });
    });
    // Visible completion feedback, while retaining server-side idempotency.
    document.querySelectorAll('form').forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (event.defaultPrevented || !form.checkValidity()) return;
            if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
                event.preventDefault();
                return;
            }
            var button = event.submitter;
            if (!button) return;
            button.setAttribute('aria-busy', 'true');
            window.setTimeout(function () { button.disabled = true; }, 0);
        });
    });
    window.addEventListener('pageshow', function () {
        document.querySelectorAll('button[aria-busy]').forEach(function (button) {
            button.disabled = false; button.removeAttribute('aria-busy');
        });
    });
})();
