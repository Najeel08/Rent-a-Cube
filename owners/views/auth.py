"""Owner registration, sign-in, dashboard and profile views."""
from django.contrib import messages
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render

from config.auth_utils import (
    hash_password,
    is_valid_email,
    login_role,
    normalize_email,
    password_matches,
    require_role,
    session_auth_hash,
    upgrade_password_if_needed,
)
from config.validation import (
    positive_integer,
    required_text,
    validate_image_upload,
    validate_phone_number,
)

from ..models import Owner


def _owner_guard(request):
    """Check if owner is logged in, redirect to login page if not."""
    return require_role(request, 'owner', 'owner_login')


def register(request):
    """Handle owner registration - validate input and create new owner."""
    if request.method == "POST":
        try:
            name = required_text(request.POST, 'name', 'Name', max_length=20)
            email = normalize_email(required_text(request.POST, 'email', 'Email address', max_length=50))
            phone = validate_phone_number(request.POST.get('phonenumber'))
            place = required_text(request.POST, 'place', 'Place', max_length=50)
            gender = required_text(request.POST, 'gender', 'Gender', max_length=15)
            workex = required_text(request.POST, 'workex', 'Work experience', max_length=25)
            password = required_text(request.POST, 'password', 'Password')
            confirm_password = required_text(request.POST, 'cpassword', 'Password confirmation')
            validate_password(password, Owner(name=name, email=email))
            image = request.FILES.get('image')
            proof = request.FILES.get('proof')
            validate_image_upload(image, 'Profile image')
            validate_image_upload(proof, 'Proof document')
        except ValidationError as exc:
            messages.info(request, '; '.join(exc.messages))
            return render(request, 'owners/register.html')

        if not is_valid_email(email):
            messages.info(request, "Please enter a valid email address (e.g. vikram@cowork.in)")
            return render(request, 'owners/register.html')

        if password != confirm_password:
            messages.info(request, 'password not match')
            return render(request, 'owners/register.html')

        if Owner.objects.filter(email__iexact=email).exists():
            messages.info(request, "email already exists")
        elif Owner.objects.filter(name=name).exists():
            messages.info(request, "user already exists")
        else:
            try:
                with transaction.atomic():
                    Owner.objects.create(
                        name=name,
                        email=email,
                        phone_number=phone,
                        place=place,
                        gender=gender,
                        password=hash_password(password),
                        image=image,
                        work_experience=workex,
                        proof_document=proof,
                    )
            except IntegrityError:
                messages.error(request, 'This email address is already registered.')
                return render(request, 'owners/register.html')
            messages.info(request, "Registration submitted. Please wait for admin approval.")
            return redirect('owner_login')

    return render(request, 'owners/register.html')


def sign_in(request):
    """Handle owner login - verify credentials and check admin approval."""
    if request.method == "POST":
        email = normalize_email(request.POST.get('email', ''))
        password = request.POST.get('password', '')
        owner = Owner.objects.filter(email__iexact=email).first()

        if password_matches(password, owner.password if owner else None) and owner:
            if owner.accept and not owner.reject:
                upgrade_password_if_needed(owner, 'password', password)
                login_role(request, 'owner', owner, owner.name)
                return redirect('owner_dashboard')
            messages.info(request, "Account not approved")
        else:
            messages.info(request, 'Invalid owner')

    return render(request, 'owners/login.html')


def dashboard(request):
    """Display owner home/dashboard page."""
    guard = _owner_guard(request)
    if guard:
        return guard
    return render(request, 'owners/dashboard.html')


def profile(request):
    """Display the owner's profile page."""
    guard = _owner_guard(request)
    if guard:
        return guard
    profile = get_object_or_404(Owner, id=request.session['id'])
    return render(request, 'owners/profile.html', {'prof': profile})


def profile_edit(request, profile_id=None):
    """Update owner profile - name, email, phone, password, image."""
    guard = _owner_guard(request)
    if guard:
        return guard
    profile = get_object_or_404(Owner, id=request.session['id'])

    if profile_id:
        try:
            profile_id = positive_integer(profile_id, 'Profile')
        except ValidationError as exc:
            messages.info(request, '; '.join(exc.messages))
            return redirect('owner_profile')
        if profile_id != profile.id:
            messages.info(request, "You can update only your own profile")
            return redirect('owner_profile')

    if request.method == "POST":
        try:
            name = required_text(request.POST, 'name', 'Name', max_length=20)
            new_email = normalize_email(
                required_text(request.POST, 'email', 'Email address', max_length=50)
            )
            if not is_valid_email(new_email):
                raise ValidationError('Please enter a valid email address.')
            new_password = request.POST.get('password')
            changing_credentials = new_email != profile.email or bool(new_password)
            if changing_credentials and not password_matches(request.POST.get('current_password', ''), profile.password):
                raise ValidationError('Enter your current password to change your email or password.')
            phone_number = validate_phone_number(request.POST.get('phonenumber'))
            work_experience = required_text(request.POST, 'workex', 'Work experience', max_length=25)
            place = required_text(request.POST, 'place', 'Place', max_length=50)
            image = request.FILES.get('image')
            if image:
                validate_image_upload(image, 'Profile image')
        except ValidationError as exc:
            messages.info(request, '; '.join(exc.messages))
            return render(request, 'owners/profile_edit.html', {'pl': profile})
        if Owner.objects.exclude(id=profile.id).filter(email=new_email).exists():
            messages.info(request, "email already exists")
            return render(request, 'owners/profile_edit.html', {'pl': profile})

        if image:
            profile.image = image

        profile.name = name
        profile.email = new_email
        profile.phone_number = phone_number
        profile.work_experience = work_experience
        profile.place = place

        confirm_password = request.POST.get("cpassword")
        if new_password:
            if new_password != confirm_password:
                messages.info(request, 'password not match')
                return render(request, 'owners/profile_edit.html', {'pl': profile})
            try:
                validate_password(new_password, profile)
            except ValidationError as exc:
                messages.error(request, '; '.join(exc.messages))
                return render(request, 'owners/profile_edit.html', {'pl': profile})
            profile.password = hash_password(new_password)

        try:
            with transaction.atomic():
                profile.save()
        except IntegrityError:
            messages.error(request, 'This email address is already registered.')
            return render(request, 'owners/profile_edit.html', {'pl': profile})
        request.session.cycle_key()
        request.session['auth_hash'] = session_auth_hash(profile)
        request.session['Name'] = profile.name
        messages.info(request, "Profile updated")
        return redirect('owner_profile')

    return render(request, 'owners/profile_edit.html', {'pl': profile})
