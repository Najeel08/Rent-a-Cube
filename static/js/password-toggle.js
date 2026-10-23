/* Shared by the administrator and technician sign-in forms. */
(function () {
    document.querySelectorAll('.portal-password-toggle').forEach(function (button) {
        var input = document.getElementById(button.getAttribute('aria-controls'));
        if (!input) return;
        button.hidden = false;
        button.addEventListener('click', function () {
            var show = input.type === 'password';
            input.type = show ? 'text' : 'password';
            button.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
            button.setAttribute('aria-pressed', String(show));
            button.querySelector('i').className = show ? 'fa fa-eye' : 'fa fa-eye-slash';
        });
    });
})();
