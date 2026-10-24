const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const root = path.resolve(__dirname, '../..');

function registrationPage(template, formId, phoneId) {
    const html = fs.readFileSync(path.join(root, 'templates', template), 'utf8');
    const elements = new Map();
    const document = { getElementById: id => elements.get(id), activeElement: null };
    for (const [, id] of html.matchAll(/\bid="([^"]+)"/g)) {
        elements.set(id, {
            value: '', textContent: '', className: '', style: {}, listeners: {},
            addEventListener(name, listener) { this.listeners[name] = listener; },
            focus() { document.activeElement = this; },
            fire(name) {
                const event = { defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } };
                this.listeners[name].call(this, event);
                return event;
            },
        });
    }
    const context = vm.createContext({ document });
    for (const [, attributes, inline] of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)) {
        if (attributes.includes('js/registration.js')) {
            vm.runInContext(fs.readFileSync(path.join(root, 'static/js/registration.js'), 'utf8'), context);
        } else if (!attributes.includes('src=')) {
            vm.runInContext(inline, context);
        }
    }
    const get = id => elements.get(id);
    get('email').value = 'alex@example.test';
    get(phoneId).value = '9876543210';
    get('password').value = get('cpassword').value = 'Valid-password!29';
    return { get, document, submit: () => get(formId).fire('submit') };
}

for (const [template, formId, phoneId] of [
    ['accounts/register.html', 'userRegForm', 'phone'],
    ['owners/register.html', 'ownerRegForm', 'phonenumber'],
]) {
    test(`${template}: email feedback preserves text and classes`, () => {
        const { get } = registrationPage(template, formId, phoneId);
        for (const [value, message, className] of [
            ['invalid', 'Enter a valid email address, such as name@example.com.', 'text-danger mt-1 d-block'],
            ['  alex@example.test  ', 'Valid email address.', 'text-success mt-1 d-block'],
            ['', '', 'text-success mt-1 d-block'],
        ]) {
            get('email').value = value;
            get('email').fire('input');
            assert.equal(get('emailError').textContent, message);
            assert.equal(get('emailError').className, className);
        }
    });

    test(`${template}: password feedback and matching remain unchanged`, () => {
        const { get } = registrationPage(template, formId, phoneId);
        get('password').fire('input');
        for (const id of ['critLength', 'critUpper', 'critLower', 'critNumber', 'critSpecial']) {
            assert.equal(get(id).style.color, '#10B981');
            assert.equal(get(id).style.fontWeight, '600');
        }
        assert.equal(get('cpasswordError').textContent, 'Passwords match.');
        get('password').value = 'weak';
        get('password').fire('input');
        assert.equal(get('critLength').style.color, '#64748B');
        assert.equal(get('critLength').style.fontWeight, 'normal');
        assert.equal(get('cpasswordError').textContent, 'Passwords do not match.');
        get('cpassword').value = '';
        get('cpassword').fire('input');
        assert.equal(get('cpasswordError').textContent, '');
    });

    test(`${template}: submission preserves validation order, focus and password limits`, () => {
        const { get, document, submit } = registrationPage(template, formId, phoneId);
        for (const [id, value, errorId, message] of [
            ['email', 'invalid', 'emailError', 'Enter a valid email address, such as name@example.com.'],
            [phoneId, '1234567890', 'phoneError', 'Enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.'],
            ['password', 'weak', 'passwordError', 'Use 8 to 20 characters with uppercase, lowercase, a number, and a special character.'],
            ['password', 'Aa1!' + 'x'.repeat(17), 'passwordError', 'Use 8 to 20 characters with uppercase, lowercase, a number, and a special character.'],
            ['cpassword', 'Different-password!29', 'cpasswordError', 'Passwords do not match.'],
        ]) {
            const original = get(id).value;
            get(id).value = value;
            assert.equal(submit().defaultPrevented, true);
            assert.equal(document.activeElement, get(id));
            assert.equal(get(errorId).textContent, message);
            get(id).value = original;
        }
        for (const password of ['Ab1!xxxx', 'Aa1!' + 'x'.repeat(16)]) {
            get('password').value = get('cpassword').value = password;
            assert.equal(submit().defaultPrevented, false);
        }
    });
}
