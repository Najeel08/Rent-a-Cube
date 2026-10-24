"""Owner listing management and shared listing validation."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from config.pagination import render_page
from config.validation import (
    MAX_HOURLY_PRICE,
    positive_integer,
    required_text,
    validate_image_upload,
)

from ..models import Workspace
from .auth import _owner_guard


def _workspace_fields(form_data):
    """Validate the same explicit field allowlist for listing creation and edits."""
    return {
        'name': required_text(form_data, 'name', 'Workspace name', max_length=20),
        'square_feet': required_text(form_data, 'sqft', 'Square footage', max_length=50),
        'state': required_text(form_data, 'state', 'State', max_length=80),
        'city': required_text(form_data, 'city', 'City', max_length=50),
        'location': required_text(form_data, 'location', 'Location', max_length=60),
        'hourly_rate': str(positive_integer(form_data.get('price'), 'Hourly price', MAX_HOURLY_PRICE)),
        'postal_code': required_text(form_data, 'pincode', 'Pincode', max_length=25),
        'workspace_type': required_text(form_data, 'type', 'Workspace type', max_length=80),
        'amenities': required_text(form_data, 'facility', 'Facilities', max_length=50),
        'capacity': required_text(form_data, 'capability', 'Capacity', max_length=60),
    }


def workspace_create(request):
    """Add a new workspace listing for the logged-in owner."""
    guard = _owner_guard(request)
    if guard:
        return guard

    if request.method == "POST":
        try:
            fields = _workspace_fields(request.POST)
            image = request.FILES.get('image')
            validate_image_upload(image, 'Workspace image')
        except ValidationError as exc:
            messages.info(request, '; '.join(exc.messages))
            return render(request, 'owners/workspace_create.html')
        Workspace.objects.create(**fields, image=image, owner_id=request.session['id'])
        messages.info(request, "Workspace added")
        return redirect('owner_workspace_list')

    return render(request, 'owners/workspace_create.html')


def workspace_list(request):
    """Show all workspaces owned by the logged-in owner."""
    guard = _owner_guard(request)
    if guard:
        return guard
    spaces = Workspace.objects.filter(owner_id=request.session['id'])
    return render_page(request, 'owners/workspace_list.html', 'Owvk', spaces)


def workspace_detail(request, workspace_id):
    """Show details of a specific workspace."""
    guard = _owner_guard(request)
    if guard:
        return guard
    work = get_object_or_404(Workspace, id=workspace_id, owner_id=request.session['id'])
    return render(request, 'owners/workspace_detail.html', {'Owvkd': work})


def workspace_edit(request, workspace_id):
    """Update an existing workspace listing."""
    guard = _owner_guard(request)
    if guard:
        return guard
    try:
        workspace_id = positive_integer(workspace_id, 'Workspace')
    except ValidationError as exc:
        messages.info(request, '; '.join(exc.messages))
        return redirect('owner_workspace_list')
    owner_work = get_object_or_404(Workspace, id=workspace_id, owner_id=request.session['id'])

    if request.method == "POST":
        try:
            fields = _workspace_fields(request.POST)
            if request.FILES.get('image'):
                validate_image_upload(request.FILES['image'], 'Workspace image')
        except ValidationError as exc:
            messages.info(request, '; '.join(exc.messages))
            return render(request, 'owners/workspace_edit.html', {'up': owner_work})
        if request.FILES.get("image"):
            owner_work.image = request.FILES["image"]
        for field, value in fields.items():
            setattr(owner_work, field, value)
        owner_work.save()
        messages.info(request, "Workspace updated")
        return redirect('owner_workspace_list')

    return render(request, 'owners/workspace_edit.html', {'up': owner_work})


def workspace_delete(request, workspace_id):
    """Delete an unused listing while preserving booking history and shared photos."""
    guard = _owner_guard(request)
    if guard:
        return guard
    work = get_object_or_404(Workspace, id=workspace_id, owner_id=request.session['id'])

    if request.method == "POST":
        if work.bookings.exists():
            messages.error(request, 'This workspace has booking history. It cannot be deleted.')
            return redirect('owner_workspace_list')
        try:
            work.delete()
        except ProtectedError:
            messages.error(request, 'A booking now references this workspace. It cannot be deleted.')
            return redirect('owner_workspace_list')
        messages.info(request, "Workspace deleted")
        return redirect('owner_workspace_list')

    return render(request, 'owners/workspace_delete_confirm.html', {'delete': work})
