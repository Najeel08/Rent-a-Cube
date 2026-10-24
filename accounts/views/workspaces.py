"""Customer workspace discovery and reservation views."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from config.pagination import render_page
from config.validation import (
    MAX_BOOKING_DURATION_HOURS,
    MAX_HOURLY_PRICE,
    positive_integer,
    validate_booking_date,
    validate_booking_start_time,
)
from owners.models import Owner, Workspace

from ..models import Booking
from ..reservations import has_conflict, interval
from .auth import _user_guard


def workspace_list(request):
    """Show all available workspaces from approved owners."""
    guard = _user_guard(request)
    if guard:
        return guard
    workspaces = Workspace.objects.filter(owner__accept=True, owner__reject=False).select_related('owner')
    return render_page(request, 'accounts/workspace_list.html', 'Uwvk', workspaces)


def workspace_overview(request):
    """Display workspace details page."""
    guard = _user_guard(request)
    if guard:
        return guard
    return redirect('workspace_search')


def workspace_search(request):
    """Show all workspaces with optional city search filter."""
    guard = _user_guard(request)
    if guard:
        return guard
    workspaces = Workspace.objects.filter(owner__accept=True, owner__reject=False).select_related('owner')
    city = (request.POST if request.method == 'POST' else request.GET).get('city', '').strip()[:50]
    if city:
        workspaces = workspaces.filter(city__icontains=city)
    return render_page(request, 'accounts/workspace_search_results.html', 'Up', workspaces)


@transaction.atomic
def workspace_book(request, workspace_id):
    """Show workspace details and allow user to add it to cart."""
    guard = _user_guard(request)
    if guard:
        return guard
    try:
        workspace_id = positive_integer(workspace_id, 'Workspace')
    except ValidationError as exc:
        messages.info(request, '; '.join(exc.messages))
        return redirect('workspace_search')
    workspace = get_object_or_404(Workspace.objects.select_for_update(), id=workspace_id, owner__accept=True, owner__reject=False)

    if request.method == "POST":
        try:
            hours = positive_integer(
                request.POST.get('nohrs'),
                'Number of hours',
                MAX_BOOKING_DURATION_HOURS,
            )
            booking_date = validate_booking_date(request.POST.get('date'))
            start_time = validate_booking_start_time(request.POST.get('start_time'))
            price = positive_integer(workspace.hourly_rate, 'Workspace price', MAX_HOURLY_PRICE)
        except ValidationError as exc:
            messages.info(request, '; '.join(exc.messages))
            return render(request, "accounts/workspace_booking_form.html", {'owr': [workspace]})

        if Booking.objects.filter(
            user_id=request.session['id'],
            workspace=workspace,
            date=booking_date,
            start_time=start_time,
            is_refunded=False,
            payment_review_required=False,
        ).exists():
            messages.info(request, 'This reservation is already in your cart.')
            return render(request, "accounts/workspace_booking_form.html", {'owr': [workspace]})

        candidate = Booking(workspace=workspace, date=booking_date, start_time=start_time, duration_hours=hours)
        if interval(candidate)[0] <= timezone.now():
            messages.error(request, 'Booking start time must be in the future.')
            return render(request, 'accounts/workspace_booking_form.html', {'owr': [workspace]})
        if has_conflict(candidate):
            messages.error(request, 'This workspace is reserved for the selected time.')
            return render(request, 'accounts/workspace_booking_form.html', {'owr': [workspace]})

        Booking.objects.create(
            workspace_name=workspace.name,
            hourly_rate=price,
            location=workspace.location,
            user_id=request.session['id'],
            owner_id=workspace.owner_id,
            image=workspace.image.name,
            duration_hours=hours,
            total_amount=price * hours,
            date=booking_date,
            start_time=start_time,
            workspace=workspace,
        )
        messages.info(request, "Workspace added to cart")
        return redirect('cart_owner_list')

    return render(request, "accounts/workspace_booking_form.html", {'owr': [workspace]})


def owner_public_profile(request, owner_id):
    """Show an owner's public profile."""
    guard = _user_guard(request)
    if guard:
        return guard
    try:
        owner_id = positive_integer(owner_id, 'Workspace provider')
    except ValidationError as exc:
        messages.info(request, '; '.join(exc.messages))
        return redirect('workspace_search')
    owner = get_object_or_404(Owner, id=owner_id, accept=True, reject=False)
    return render(request, 'accounts/owner_profile.html', {'uviewprof': owner})


def owner_workspace_catalog(request, owner_id):
    """Show all workspaces belonging to a specific owner."""
    guard = _user_guard(request)
    if guard:
        return guard
    try:
        owner_id = positive_integer(owner_id, 'Workspace provider')
    except ValidationError as exc:
        messages.info(request, '; '.join(exc.messages))
        return redirect('workspace_search')
    workspaces = Workspace.objects.filter(owner_id=owner_id, owner__accept=True)
    return render_page(request, "accounts/workspace_search_results.html", 'Up', workspaces)
