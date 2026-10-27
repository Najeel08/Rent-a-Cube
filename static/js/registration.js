/* Shared registration feedback; server-side validation remains authoritative. */
function setupRegistrationForm(formId, phoneId) {
    const strongRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#^()_+\-=])[A-Za-z\d@$!%*?&#^()_+\-=]{8,20}$/;
    function validateEmailField(input, errorId) {
        const email = input.value.trim();
        const errElem = document.getElementById(errorId);
        if (!errElem) return;
        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        if (!email) {
            errElem.textContent = "";
            input.removeAttribute('aria-invalid');
            return false;
        }
        if (!emailRegex.test(email)) {
            input.setAttribute('aria-invalid', 'true');
            errElem.textContent = "Enter a valid email address, such as name@example.com.";
            errElem.className = "text-danger mt-1 d-block";
            return false;
        } else {
            input.setAttribute('aria-invalid', 'false');
            errElem.textContent = "Valid email address.";
            errElem.className = "text-success mt-1 d-block";
            return true;
        }
    }

    function checkPasswordStrength() {
        const passwordInput = document.getElementById("password");
        const pwd = passwordInput.value;
        if (pwd) passwordInput.setAttribute('aria-invalid', String(!strongRegex.test(pwd)));
        else passwordInput.removeAttribute('aria-invalid');
        if (strongRegex.test(pwd)) document.getElementById("passwordError").textContent = "";

        const hasLength = pwd.length >= 8;
        const hasUpper = /[A-Z]/.test(pwd);
        const hasLower = /[a-z]/.test(pwd);
        const hasNumber = /[0-9]/.test(pwd);
        const hasSpecial = /[@$!%*?&#^()_+\-=]/.test(pwd);

        updateCriterion("critLength", hasLength);
        updateCriterion("critUpper", hasUpper);
        updateCriterion("critLower", hasLower);
        updateCriterion("critNumber", hasNumber);
        updateCriterion("critSpecial", hasSpecial);

        checkPasswordMatch();
    }

    function updateCriterion(elemId, isValid) {
        const elem = document.getElementById(elemId);
        if (!elem) return;
        if (isValid) {
            elem.style.color = "var(--rc-success-text)";
            elem.style.fontWeight = "600";
        } else {
            elem.style.color = "var(--rc-text-muted)";
            elem.style.fontWeight = "normal";
        }
    }

    function checkPasswordMatch() {
        const pwd = document.getElementById("password").value;
        const cpwd = document.getElementById("cpassword").value;
        const confirmInput = document.getElementById("cpassword");
        const cpwdErr = document.getElementById("cpasswordError");

        if (!cpwd) {
            cpwdErr.textContent = "";
            confirmInput.removeAttribute('aria-invalid');
            return;
        }

        if (pwd !== cpwd) {
            confirmInput.setAttribute('aria-invalid', 'true');
            cpwdErr.textContent = "Passwords do not match.";
            cpwdErr.className = "text-danger mt-1 d-block";
        } else {
            confirmInput.setAttribute('aria-invalid', 'false');
            cpwdErr.textContent = "Passwords match.";
            cpwdErr.className = "text-success mt-1 d-block";
        }
    }

    function validatePhoneField() {
        const phoneInput = document.getElementById(phoneId);
        const valid = /^[6-9][0-9]{9}$/.test(phoneInput.value.trim());
        const phoneErr = document.getElementById("phoneError");
        phoneInput.setAttribute('aria-invalid', String(!valid));
        phoneErr.textContent = valid ? "" : "Enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.";
        return valid;
    }

    function validateForm() {
        const emailInput = document.getElementById("email");
        if (!validateEmailField(emailInput, "emailError")) {
            emailInput.focus();
            return false;
        }

        if (!validatePhoneField()) {
            document.getElementById(phoneId).focus();
            return false;
        }

        const pwd = document.getElementById("password").value;
        const cpwd = document.getElementById("cpassword").value;
        const pwdErr = document.getElementById("passwordError");

        if (!strongRegex.test(pwd)) {
            document.getElementById("password").setAttribute('aria-invalid', 'true');
            pwdErr.textContent = "Use 8 to 20 characters with uppercase, lowercase, a number, and a special character.";
            document.getElementById("password").focus();
            return false;
        } else {
            pwdErr.textContent = "";
            document.getElementById("password").setAttribute('aria-invalid', 'false');
        }

        if (pwd !== cpwd) {
            document.getElementById("cpassword").setAttribute('aria-invalid', 'true');
            document.getElementById("cpasswordError").textContent = "Passwords do not match.";
            document.getElementById("cpassword").focus();
            return false;
        }

        document.getElementById("cpassword").setAttribute('aria-invalid', 'false');
        return true;
    }

    document.getElementById(formId).addEventListener('submit', function (event) { if (!validateForm()) event.preventDefault(); });
    document.getElementById('email').addEventListener('input', function (event) { validateEmailField(this, 'emailError'); });
    document.getElementById(phoneId).addEventListener('input', function () {
        if (this.getAttribute('aria-invalid') === 'true') validatePhoneField();
    });
    document.getElementById('password').addEventListener('input', function () { checkPasswordStrength(); });
    document.getElementById('cpassword').addEventListener('input', function () { checkPasswordMatch(); });
}
