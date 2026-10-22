from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib.auth.decorators import user_passes_test

from .models import Resource, ResourceCategory
from .forms import ResourceForm, ResourceCategoryForm


# Only admin can manage resources
admin_only = user_passes_test(lambda user: user.is_superuser)


# 1. Browse, search, and filter resources
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


# 2. Show one resource
def resource_detail(request, pk):
    resource = get_object_or_404(Resource, pk=pk)

    return render(request, "resources/resource_detail.html", {
        "resource": resource,
    })


# 3. Create a resource (Admin only)
@admin_only
def resource_create(request):
    if request.method == "POST":
        form = ResourceForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("resources:resource_list")
    else:
        form = ResourceForm()

    return render(request, "resources/resource_form.html", {
        "form": form,
    })


# 4. Update a resource (Admin only)
@admin_only
def resource_update(request, pk):
    resource = get_object_or_404(Resource, pk=pk)

    if request.method == "POST":
        form = ResourceForm(request.POST, instance=resource)

        if form.is_valid():
            form.save()
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


# 5. Delete a resource (Admin only)
@admin_only
def resource_delete(request, pk):
    resource = get_object_or_404(Resource, pk=pk)

    if request.method == "POST":
        resource.delete()
        return redirect("resources:resource_list")

    return render(request, "resources/resource_confirm_delete.html", {
        "resource": resource,
    })


# 6. Show all categories
def category_list(request):
    categories = ResourceCategory.objects.all()

    return render(request, "resources/category_list.html", {
        "categories": categories,
    })


# 7. Create a category
def category_create(request):
    if request.method == "POST":
        form = ResourceCategoryForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("resources:category_list")
    else:
        form = ResourceCategoryForm()

    return render(request, "resources/category_form.html", {
        "form": form,
    })


# 8. Check resource availability
def check_availability(resource_id, start_time, end_time):
    return not Resource.objects.filter(
        pk=resource_id,
        bookings__start_time__lt=end_time,
        bookings__end_time__gt=start_time,
        bookings__status="Confirmed",
    ).exists()


# 9. Calculate resource utilization
def get_utilization_rate(resource):
    from bookings.models import Booking

    return Booking.objects.filter(resource=resource).count()
