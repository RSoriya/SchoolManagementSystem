from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts.permissions import admin_required
from apps.academics.forms import EnrollStudentForm, TransferEnrollmentForm
from apps.academics.models import CourseClass, Enrollment
from apps.academics.services import enroll_student, set_enrollment_status, transfer_enrollment
from apps.audit.models import AuditEvent
from apps.audit.services import log_event
from apps.billing.services import PAYABLE_STATUSES
from apps.core.pagination import extra_query, paginate, per_page_value

from .forms import StudentForm
from .models import Student
from .payloads import student_payload


def _student_list_response(request, form=None, open_form_modal=False):
    query = request.GET.get("q", "").strip()
    class_id = request.GET.get("class", "").strip()
    students = Student.objects.all()
    if query:
        students = students.filter(
            Q(student_id__icontains=query)
            | Q(name_kh__icontains=query)
            | Q(name_en__icontains=query)
            | Q(phone__icontains=query)
        )
    if class_id:
        students = students.filter(
            enrollments__course_class_id=class_id,
            enrollments__status=Enrollment.Status.ACTIVE,
        ).distinct()
    page = paginate(request, students)
    return render(
        request,
        "students/list.html",
        {
            "page_title": "សិស្ស",
            "students": page,
            "query": query,
            "class_id": class_id,
            "classes": CourseClass.objects.filter(is_active=True).select_related("course"),
            "form": form or StudentForm(),
            "payloads": {str(item.pk): student_payload(item) for item in page.object_list},
            "open_form_modal": open_form_modal,
            "create_url": reverse("students:create"),
            "per_page": per_page_value(request),
            "extra_query": extra_query(request),
        },
    )


@admin_required
@require_GET
def student_list(request):
    return _student_list_response(request)


@admin_required
@require_http_methods(["GET", "POST"])
def student_create(request):
    form = StudentForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        student = form.save(commit=False)
        student.created_by = request.user
        student.save()
        log_event(
            action=AuditEvent.Action.STUDENT_CREATED,
            summary=f"បង្កើតសិស្ស {student.student_id} · {student.name_kh}",
            user=request.user,
            obj=student,
        )
        messages.success(request, f"បានបង្កើតសិស្ស {student.student_id} រួចរាល់។")
        return redirect("students:list")
    if request.method == "POST" and request.POST.get("from_modal"):
        return _student_list_response(request, form=form, open_form_modal=True)
    return render(
        request,
        "students/form.html",
        {"page_title": "បន្ថែមសិស្ស", "form": form, "student": None},
    )


@admin_required
@require_GET
def student_detail(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    enrollments = student.enrollments.select_related("course_class__course", "transferred_from")
    enroll_form = EnrollStudentForm(student=student)
    payments = student.payments.select_related("receipt", "method", "course_class").order_by("-paid_on", "-created_at")
    context = {
        "page_title": student.display_name,
        "student": student,
        "enrollments": enrollments,
        "enroll_form": enroll_form,
        "can_enroll": enroll_form.fields["course_class"].queryset.exists(),
        "active_enrollments": enrollments.filter(status=Enrollment.Status.ACTIVE),
        "payments": payments,
        "can_pay": enrollments.filter(status__in=PAYABLE_STATUSES).exists(),
    }
    return render(request, "students/detail.html", context)


@admin_required
@require_http_methods(["GET", "POST"])
def student_edit(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    form = StudentForm(request.POST or None, request.FILES or None, instance=student)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_event(
            action=AuditEvent.Action.STUDENT_UPDATED,
            summary=f"កែសិស្ស {student.student_id} · {student.name_kh}",
            user=request.user,
            obj=student,
        )
        messages.success(request, "បានរក្សាទុកព័ត៌មានសិស្ស។")
        return redirect("students:list")
    if request.method == "POST" and request.POST.get("from_modal"):
        return _student_list_response(request, form=form, open_form_modal=True)
    return render(
        request,
        "students/form.html",
        {"page_title": f"កែសិស្ស · {student.student_id}", "form": form, "student": student},
    )


@admin_required
@require_POST
def student_delete(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    if student.enrollments.exists():
        messages.error(request, "មិនអាចលុបសិស្សដែលមានប្រវត្តិចុះឈ្មោះ។")
        return redirect("students:list")
    log_event(
        action=AuditEvent.Action.STUDENT_DELETED,
        summary=f"លុបសិស្ស {student.student_id} · {student.name_kh}",
        user=request.user,
        extra={"student_id": student.student_id},
        obj=student,
    )
    student.delete()
    messages.success(request, "បានលុបសិស្ស។")
    return redirect("students:list")


@admin_required
@require_POST
def enroll(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    form = EnrollStudentForm(request.POST, student=student)
    if form.is_valid():
        try:
            enroll_student(
                student,
                form.cleaned_data["course_class"],
                user=request.user,
                note=form.cleaned_data.get("note") or "",
                next_due_date=form.cleaned_data.get("next_due_date"),
            )
            messages.success(request, "បានចុះឈ្មោះសិស្សក្នុងថ្នាក់។")
        except ValidationError as exc:
            messages.error(request, exc.messages[0] if hasattr(exc, "messages") else str(exc))
    else:
        messages.error(request, "សូមជ្រើសថ្នាក់រៀន។")
    return redirect(student)


@admin_required
@require_http_methods(["GET", "POST"])
def transfer(request, student_id, enrollment_id):
    student = get_object_or_404(Student, student_id=student_id)
    enrollment = get_object_or_404(Enrollment, pk=enrollment_id, student=student)
    form = TransferEnrollmentForm(request.POST or None, enrollment=enrollment)
    if request.method == "POST" and form.is_valid():
        try:
            transfer_enrollment(
                enrollment,
                form.cleaned_data["course_class"],
                user=request.user,
                note=form.cleaned_data.get("note") or "",
            )
            messages.success(request, "បានផ្ទេរថ្នាក់។ ប្រវត្តិចាស់នៅតែរក្សាទុក។")
            return redirect(student)
        except ValidationError as exc:
            messages.error(request, exc.messages[0] if hasattr(exc, "messages") else str(exc))
    return render(
        request,
        "students/transfer.html",
        {
            "page_title": "ផ្ទេរថ្នាក់",
            "student": student,
            "enrollment": enrollment,
            "form": form,
        },
    )


@admin_required
@require_POST
def change_status(request, student_id, enrollment_id, action):
    student = get_object_or_404(Student, student_id=student_id)
    enrollment = get_object_or_404(Enrollment, pk=enrollment_id, student=student)
    status_map = {
        "suspend": Enrollment.Status.SUSPENDED,
        "resume": Enrollment.Status.ACTIVE,
        "drop": Enrollment.Status.DROPPED,
        "complete": Enrollment.Status.COMPLETED,
    }
    status = status_map.get(action)
    if not status:
        messages.error(request, "សកម្មភាពមិនត្រឹមត្រូវ។")
        return redirect(student)
    try:
        set_enrollment_status(enrollment, status, user=request.user, note=request.POST.get("note", ""))
        messages.success(request, "បានប្ដូរស្ថានភាពការសិក្សា។")
    except ValidationError as exc:
        messages.error(request, exc.messages[0] if hasattr(exc, "messages") else str(exc))
    return redirect(student)
