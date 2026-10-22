(function () {
    var sidebar = document.getElementById('sidebar');
    var toggle = document.getElementById('sidebarCollapse');
    if (!sidebar || !toggle) return;
    toggle.setAttribute('aria-controls', 'sidebar');
    toggle.setAttribute('aria-label', 'Toggle navigation');
    function sync() {
        var mobile = window.matchMedia('(max-width: 991px)').matches;
        var open = mobile ? sidebar.classList.contains('is-open') : !sidebar.classList.contains('is-collapsed');
        toggle.setAttribute('aria-expanded', String(open));
        sidebar.inert = !open;
        document.body.classList.toggle('admin-nav-collapsed', !mobile && !open);
    }
    toggle.addEventListener('click', function () {
        sidebar.classList.toggle(window.matchMedia('(max-width: 991px)').matches ? 'is-open' : 'is-collapsed');
        sync();
    });
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            sidebar.classList.remove('is-open');
            sync();
            toggle.focus();
        }
    });
    document.addEventListener('click', function (event) {
        if (!sidebar.contains(event.target) && !toggle.contains(event.target)) {
            sidebar.classList.remove('is-open');
            sync();
        }
    });
    document.querySelectorAll('.admin-sidebar-link.dropdown-toggle').forEach(function (link) {
        link.addEventListener('click', function (event) {
            event.preventDefault();
            var target = document.getElementById((link.getAttribute('href') || '').slice(1));
            if (!target) return;
            link.setAttribute('aria-expanded', String(target.classList.toggle('show')));
        });
    });
    window.addEventListener('resize', sync);
    sync();
})();
