(function () {
    function closeMenu(header) {
        var toggle = header.querySelector('[data-nav-toggle]');
        var panel = header.querySelector('.cube-nav-panel');
        if (toggle) {
            toggle.setAttribute('aria-expanded', 'false');
            toggle.setAttribute('aria-label', 'Open navigation');
        }
        if (panel) {
            panel.classList.remove('is-open');
        }
        header.querySelectorAll('[data-nav-dropdown]').forEach(function (button) {
            var submenu = document.getElementById(button.getAttribute('aria-controls'));
            button.setAttribute('aria-expanded', 'false');
            if (submenu) {
                submenu.hidden = true;
            }
        });
        header.querySelectorAll('.dropdown.show').forEach(function (dropdown) {
            dropdown.classList.remove('show');
            var dropdownToggle = dropdown.querySelector('.dropdown-toggle');
            if (dropdownToggle) {
                dropdownToggle.setAttribute('aria-expanded', 'false');
            }
        });
    }

    function setupPortalNavbar(header, index) {
        if (header.querySelector('.cube-nav-panel')) {
            return;
        }
        var links = header.querySelector('.cube-nav-links');
        if (!links) {
            return;
        }
        var row = header.querySelector(':scope > .container') || header;
        var brand = row.querySelector('.navbar-brand');
        var brandContainer = Array.prototype.find.call(row.children, function (child) {
            return child.contains(brand);
        });
        var originalParent = links.parentElement;
        var panel = originalParent.tagName === 'NAV' ? originalParent : document.createElement('nav');
        var panelId = 'portal-navbar-' + index;
        panel.classList.add('cube-nav-panel');
        panel.id = panelId;
        panel.setAttribute('aria-label', 'Portal navigation');
        panel.classList.remove('d-none', 'd-md-flex', 'd-lg-flex');
        links.classList.remove('d-none', 'd-md-flex', 'd-lg-flex');
        if (panel !== originalParent) {
            links.parentNode.insertBefore(panel, links);
            panel.appendChild(links);
        }

        var toggle = document.createElement('button');
        toggle.className = 'cube-nav-toggle';
        toggle.type = 'button';
        toggle.setAttribute('data-nav-toggle', '');
        toggle.setAttribute('aria-controls', panelId);
        toggle.setAttribute('aria-expanded', 'false');
        toggle.setAttribute('aria-label', 'Open navigation');
        toggle.innerHTML = '<i class="fa fa-bars" aria-hidden="true"></i>';
        if (brandContainer) {
            brandContainer.insertAdjacentElement('afterend', toggle);
        } else {
            row.insertBefore(toggle, panel);
        }
        Array.prototype.forEach.call(row.children, function (child) {
            if (child !== brandContainer && child !== panel && child !== toggle && child.classList.contains('d-flex')) {
                child.classList.add('cube-nav-actions');
                panel.appendChild(child);
            }
        });
        header.classList.add('cube-portal-navbar');
        row.classList.add('cube-navbar-row');
    }

    function setupNavbar(header, index) {
        if (!header.classList.contains('cube-responsive-navbar')) {
            setupPortalNavbar(header, index);
        }
        var toggle = header.querySelector('[data-nav-toggle]');
        var panel = header.querySelector('.cube-nav-panel');
        if (!toggle || !panel) {
            return;
        }
        toggle.addEventListener('click', function () {
            var isOpen = panel.classList.toggle('is-open');
            toggle.setAttribute('aria-expanded', String(isOpen));
            toggle.setAttribute('aria-label', isOpen ? 'Close navigation' : 'Open navigation');
        });
        header.querySelectorAll('[data-nav-dropdown]').forEach(function (button) {
            button.addEventListener('click', function () {
                var submenu = document.getElementById(button.getAttribute('aria-controls'));
                if (!submenu) {
                    return;
                }
                var isOpen = submenu.hidden;
                header.querySelectorAll('[data-nav-dropdown]').forEach(function (otherButton) {
                    var otherMenu = document.getElementById(otherButton.getAttribute('aria-controls'));
                    otherButton.setAttribute('aria-expanded', 'false');
                    if (otherMenu) {
                        otherMenu.hidden = true;
                    }
                });
                submenu.hidden = !isOpen;
                button.setAttribute('aria-expanded', String(isOpen));
            });
        });
        panel.addEventListener('click', function (event) {
            if (event.target.closest('a[href]')) {
                closeMenu(header);
            }
        });
        header.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') {
                closeMenu(header);
                toggle.focus();
            }
        });
    }

    function init() {
        var headers = document.querySelectorAll('.cube-navbar');
        headers.forEach(setupNavbar);
        document.addEventListener('click', function (event) {
            headers.forEach(function (header) {
                if (!header.contains(event.target)) {
                    closeMenu(header);
                }
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
