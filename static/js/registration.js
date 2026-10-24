/* Shared registration feedback; server-side validation remains authoritative. */
function setupRegistrationForm(formId, phoneId) {
    function validateEmailField(input, errorId) {
        const email = input.value.trim();
        const errElem = document.getElementById(errorId);
        if (!errElem) return;
        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        if (!email) {
            errElem.textContent = "";
            return false;
        }
        if (!emailRegex.test(email)) {
            errElem.textContent = "Enter a valid email address, such as name@example.com.";
            errElem.className = "text-danger mt-1 d-block";
            return false;
        } else {
            errElem.textContent = "Valid email address.";
            errElem.className = "text-success mt-1 d-block";
            return true;
        }
    }

    function checkPasswordStrength() {
        const pwd = document.getElementById("password").value;

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
            elem.style.color = "#10B981";
            elem.style.fontWeight = "600";
        } else {
            elem.style.color = "#64748B";
            elem.style.fontWeight = "normal";
        }
    }

    function checkPasswordMatch() {
        const pwd = document.getElementById("password").value;
        const cpwd = document.getElementById("cpassword").value;
        const cpwdErr = document.getElementById("cpasswordError");

        if (!cpwd) {
            cpwdErr.textContent = "";
            return;
        }

        if (pwd !== cpwd) {
            cpwdErr.textContent = "Passwords do not match.";
            cpwdErr.className = "text-danger mt-1 d-block";
        } else {
            cpwdErr.textContent = "Passwords match.";
            cpwdErr.className = "text-success mt-1 d-block";
        }
    }

    function validateForm() {
        const emailInput = document.getElementById("email");
        if (!validateEmailField(emailInput, "emailError")) {
            emailInput.focus();
            return false;
        }

        const phone = document.getElementById(phoneId).value.trim();
        const phoneErr = document.getElementById("phoneError");
        if (!/^[6-9][0-9]{9}$/.test(phone)) {
            phoneErr.textContent = "Enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.";
            document.getElementById(phoneId).focus();
            return false;
        } else {
            phoneErr.textContent = "";
        }

        const pwd = document.getElementById("password").value;
        const cpwd = document.getElementById("cpassword").value;
        const pwdErr = document.getElementById("passwordError");

        const strongRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#^()_+\-=])[A-Za-z\d@$!%*?&#^()_+\-=]{8,20}$/;
        if (!strongRegex.test(pwd)) {
            pwdErr.textContent = "Use 8 to 20 characters with uppercase, lowercase, a number, and a special character.";
            document.getElementById("password").focus();
            return false;
        } else {
            pwdErr.textContent = "";
        }

        if (pwd !== cpwd) {
            document.getElementById("cpasswordError").textContent = "Passwords do not match.";
            document.getElementById("cpassword").focus();
            return false;
        }

        return true;
    }

    document.getElementById(formId).addEventListener('submit', function (event) { if (!validateForm()) event.preventDefault(); });
    document.getElementById('email').addEventListener('input', function (event) { validateEmailField(this, 'emailError'); });
    document.getElementById('password').addEventListener('input', function () { checkPasswordStrength(); });
    document.getElementById('cpassword').addEventListener('input', function () { checkPasswordMatch(); });
}
