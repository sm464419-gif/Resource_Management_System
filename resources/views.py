
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST

from .models import Resource, ResourceCategory
from .forms import ResourceForm, ResourceCategoryForm
from bookings.models import Booking
import qrcode
import base64

from io import BytesIO
from django.urls import reverse


# ==========================================
# ADMIN PERMISSION
# ==========================================

def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or getattr(user, "role", "") == "admin"
    )


admin_only = user_passes_test(is_admin)


# ==========================================
# 1. RESOURCE LIST
# ==========================================

def resource_list(request):
    resources = Resource.objects.all()
    categories = ResourceCategory.objects.all()

    search = request.GET.get("q", "")
    category = request.GET.get("category", "")

    if search:
        resources = resources.filter(
            Q(name__icontains=search) |
            Q(location__icontains=search) |
            Q(department__icontains=search)
        )

    if category:
        resources = resources.filter(category_id=category)

    return render(request, "resources/resource_list.html", {
        "resources": resources,
        "categories": categories,
    })


# ==========================================
# 2. RESOURCE DETAIL
# ==========================================

def resource_detail(request, pk):
    resource = get_object_or_404(Resource, pk=pk)

    # Create the resource URL with its unique QR token
    resource_url = request.build_absolute_uri(
        reverse('resources:resource_detail', kwargs={'pk': resource.pk})
    ) + f'?qr={resource.qr_code}'

    # Generate QR image
    qr = qrcode.make(resource_url)

    buffer = BytesIO()
    qr.save(buffer, format='PNG')

    qr_image = base64.b64encode(
        buffer.getvalue()
    ).decode('utf-8')

    return render(request, "resources/resource_detail.html", {
        "resource": resource,
        "qr_image": qr_image,
    })


# ==========================================
# 3. CREATE RESOURCE (ADMIN ONLY)
# ==========================================

@login_required
@admin_only
def resource_create(request):

    if request.method == "POST":
        form = ResourceForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Resource created successfully!"
            )

            return redirect("resources:resource_list")

    else:
        form = ResourceForm()

    return render(request, "resources/resource_form.html", {
        "form": form,
    })


# ==========================================
# 4. UPDATE RESOURCE (ADMIN ONLY)
# ==========================================

@login_required
@admin_only
def resource_update(request, pk):

    resource = get_object_or_404(Resource, pk=pk)

    if request.method == "POST":
        form = ResourceForm(request.POST, instance=resource)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Resource updated successfully!"
            )

            return redirect(
                "resources:resource_detail",
                pk=resource.pk
            )

    else:
        form = ResourceForm(instance=resource)

    return render(request, "resources/resource_form.html", {
        "form": form,
        "resource": resource,
    })


# ==========================================
# 5. DELETE RESOURCE (ADMIN ONLY)
# ==========================================

@login_required
@admin_only
def resource_delete(request, pk):

    resource = get_object_or_404(Resource, pk=pk)

    if request.method == "POST":
        resource.delete()

        messages.success(
            request,
            "Resource deleted successfully!"
        )

        return redirect("resources:resource_list")

    return render(request, "resources/resource_confirm_delete.html", {
        "resource": resource,
    })


# ==========================================
# 6. CATEGORY MANAGEMENT
# ADD, EDIT AND LIST ON ONE PAGE
# ==========================================

@login_required
@admin_only
def category_list(request):

    # Check whether the admin wants to edit a category
    edit_id = request.GET.get("edit")

    category = None

    if edit_id:
        category = get_object_or_404(
            ResourceCategory,
            pk=edit_id
        )

    # Handle category form submission
    if request.method == "POST":

        form = ResourceCategoryForm(
            request.POST,
            instance=category
        )

        if form.is_valid():
            form.save()

            if category:
                messages.success(
                    request,
                    "Category updated successfully!"
                )
            else:
                messages.success(
                    request,
                    "Category created successfully!"
                )

            return redirect("resources:category_list")

    else:

        form = ResourceCategoryForm(instance=category)

    # Get all categories
    categories = ResourceCategory.objects.all()

    return render(request, "resources/category_management.html", {
        "categories": categories,
        "form": form,
        "editing": category is not None,
    })


# ==========================================
# 7. DELETE CATEGORY (ADMIN ONLY)
# ==========================================

@login_required
@admin_only
@require_POST
def category_delete(request, pk):

    category = get_object_or_404(
        ResourceCategory,
        pk=pk
    )

    category.delete()

    messages.success(
        request,
        "Category deleted successfully!"
    )

    return redirect("resources:category_list")


# ==========================================
# 8. CHECK RESOURCE AVAILABILITY
# ==========================================

def check_availability(resource_id, start_time, end_time):

    return not Resource.objects.filter(
        pk=resource_id,
        bookings__start_time__lt=end_time,
        bookings__end_time__gt=start_time,
        bookings__status="Confirmed",
    ).exists()


# ==========================================
# 9. RESOURCE UTILIZATION
# ==========================================

def get_utilization_rate(resource):



    return Booking.objects.filter(
        resource=resource
    ).count()
