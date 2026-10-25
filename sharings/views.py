from django.utils import timezone

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from resources.models import Resource
from .models import SharedPool, SharingRequest


# Create your views here.
def shared_pool_list(request):
    pools = SharedPool.objects.filter(status="Available")

    return render(
        request,"sharings/shared_pool.html",{"pools": pools}
    )

@login_required
@require_POST
def release_to_pool(request):
    resource_id = request.POST.get("resource_id")
    available_from = parse_datetime(
        request.POST.get("available_from", "")
    )
    available_until = parse_datetime(
        request.POST.get("available_until", "")
    )

    if not resource_id or not available_from or not available_until:
        messages.error(
            request,"Please provide all required information."
        )
        return redirect("sharings:shared_pool")

    if available_from >= available_until:
        messages.error(
            request,"The end time must be after the start time."
        )
        return redirect("sharings:shared_pool")

    resource = get_object_or_404(Resource, pk=resource_id)

    SharedPool.objects.create(
        resource=resource,
        released_by=request.user.get_username(),
        available_from=available_from,
        available_until=available_until,
        status="Available"
    )

    messages.success(
        request,"Resource released to the shared pool."
    )
    return redirect("sharings:shared_pool")


@login_required
@require_POST
def withdraw_from_pool(request, pool_id):
    pool = get_object_or_404(SharedPool, pk=pool_id)

    if pool.released_by != request.user.get_username():
        messages.error(
            request,
            "You cannot withdraw this resource."
        )
        return redirect("sharings:shared_pool")

    pool.status = "Withdrawn"
    pool.save(update_fields=["status"])

    messages.success(
        request,"Resource withdrawn from the pool."
    )
    return redirect("sharings:shared_pool")

@login_required
def request_share(request, pool_id):
    pool = get_object_or_404(
        SharedPool,
        pk=pool_id,
        status="Available"
    )

    if request.method == "POST":
        start_time = parse_datetime(
            request.POST.get("start_time", "")
        )
        end_time = parse_datetime(
            request.POST.get("end_time", "")
        )
        department = request.POST.get(
            "requesting_department", ""
        ).strip()

        if not start_time or not end_time or not department:
            messages.error(
                request,"Please fill in all required fields."
            )

        elif start_time >= end_time:
            messages.error(
                request,"The end time must be after the start time."
            )

        elif (
            start_time < pool.available_from or end_time > pool.available_until ):
            messages.error(
                request,"Requested time must be within the availability window."
            )

        else:
            SharingRequest.objects.create(
                shared_pool=pool,
                requesting_department=department,
                requested_by=request.user.pk,
                start_time=start_time,
                end_time=end_time,
                status="Pending",
                decided_at=timezone.now()
            )

            messages.success(
                request,"Sharing request submitted successfully."
            )
            return redirect("sharings:shared_requests")

    return render(request,"sharings/request_create.html",{"pool": pool})

@login_required
def sharing_request_list(request):
    sharing_requests = SharingRequest.objects.filter(requested_by=request.user.pk).order_by("-pk")
    status = request.GET.get("status", "").strip().capitalize()

    if status in ["Pending", "Approved", "Rejected"]:
        sharing_requests = sharing_requests.filter(status=status)

    return render(
        request,"sharings/sharing_requests.html",{"sharing_requests": sharing_requests}
    )

@login_required
def sharing_request_detail(request, request_id):
    sharing_request = get_object_or_404(SharingRequest,pk=request_id)
    is_requester = (sharing_request.requested_by == request.user.pk)
    is_pool_owner = (sharing_request.shared_pool.released_by == request.user.get_username())

    if not (is_requester or is_pool_owner):
        messages.error(
            request,"You are not allowed to view this request."
        )
        return redirect("sharings:shared_requests")

    return render(request,"sharings/sharing_request_detail.html",{"sharing_request": sharing_request})

@login_required
@require_POST
def approve_request(request, request_id):
    sharing_request = get_object_or_404(SharingRequest,pk=request_id)
    is_pool_owner = (sharing_request.shared_pool.released_by== request.user.get_username())

    if not is_pool_owner:
        messages.error(
            request,"You cannot approve this request."
        )

    elif sharing_request.status != "Pending":
        messages.error(
            request,"This request has already been decided."
        )

    else:
        sharing_request.status = "Approved"
        sharing_request.approved_by = request.user
        sharing_request.decided_at = timezone.now()
        sharing_request.save()
        messages.success(request,"Sharing request approved.")

    return redirect("sharings:request_detail",request_id=sharing_request.pk)

@login_required
@require_POST
def reject_request(request, request_id):
    sharing_request = get_object_or_404(SharingRequest,pk=request_id)
    is_pool_owner = (sharing_request.shared_pool.released_by== request.user.get_username())

    if not is_pool_owner:
        messages.error(
            request,"You cannot reject this request."
        )

    elif sharing_request.status != "Pending":
        messages.error(
            request,"This request has already been decided."
        )

    else:
        sharing_request.status = "Rejected"
        sharing_request.approved_by = request.user
        sharing_request.decided_at = timezone.now()
        sharing_request.save()
        messages.success(request,"Sharing request rejected.")

    return redirect("sharings:request_detail",request_id=sharing_request.pk
    )
