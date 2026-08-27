from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts.permissions import admin_required
from apps.core.pagination import extra_query, paginate, per_page_value
from apps.students.models import Student

from .forms import CourseClassForm, CourseForm, EnrollIntoClassForm
from .models import Course, CourseClass, Enrollment
from .payloads import class_payload, course_payload
from .services import enroll_student


def _class_list_response(request, form=None, open_form_modal=False):
    query = request.GET.get("q", "").strip()
    course_id = request.GET.get("course", "").strip()
    classes = CourseClass.objects.select_related("course").annotate(
        active_students=Count(
            "enrollments",
            filter=Q(enrollments__status=Enrollment.Status.ACTIVE),
        )
    ).order_by("name")
    if query:
        classes = classes.filter(
            Q(name__icontains=query)
            | Q(instructor_name__icontains=query)
            | Q(course__name__icontains=query)
        )
    if course_id.isdigit():
        classes = classes.filter(course_id=course_id)
    page = paginate(request, classes)
    initial = {}
    if course_id.isdigit() and form is None:
        initial["course"] = course_id
    return render(
        request,
        "academics/class_list.html",
        {
            "page_title": "ថ្នាក់រៀន",
            "classes": page,
            "query": query,
            "course_id": course_id,
            "courses": Course.objects.filter(is_active=True),
            "form": form or CourseClassForm(initial=initial),
            "payloads": {str(item.pk): class_payload(item) for item in page.object_list},
            "open_form_modal": open_form_modal,
            "create_url": reverse("academics:class_create"),
            "per_page": per_page_value(request),
            "extra_query": extra_query(request),
        },
    )


def _course_list_response(request, form=None, open_form_modal=False):
    query = request.GET.get("q", "").strip()
    courses = Course.objects.annotate(class_count=Count("classes")).order_by("name")
    if query:
        courses = courses.filter(Q(name__icontains=query) | Q(name_kh__icontains=query))
    page = paginate(request, courses)
    return render(
        request,
        "academics/course_list.html",
        {
            "page_title": "វគ្គសិក្សា",
            "courses": page,
            "query": query,
            "form": form or CourseForm(),
            "payloads": {str(item.pk): course_payload(item) for item in page.object_list},
            "open_form_modal": open_form_modal,
            "create_url": reverse("academics:course_create"),
            "per_page": per_page_value(request),
            "extra_query": extra_query(request),
        },
    )


@admin_required
@require_GET
def course_list(request):
    return _course_list_response(request)


@admin_required
@require_http_methods(["GET", "POST"])
def course_create(request):
    form = CourseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        course = form.save()
        messages.success(request, "បានបង្កើតវគ្គសិក្សា។")
        return redirect("academics:course_list")
    if request.method == "POST" and request.POST.get("from_modal"):
        return _course_list_response(request, form=form, open_form_modal=True)
    return render(
        request,
        "academics/course_form.html",
        {"page_title": "បន្ថែមវគ្គសិក្សា", "form": form, "course": None},
    )


@admin_required
@require_GET
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    classes = course.classes.annotate(
        active_students=Count(
            "enrollments",
            filter=Q(enrollments__status=Enrollment.Status.ACTIVE),
        )
    )
    return render(
        request,
        "academics/course_detail.html",
        {"page_title": course.name, "course": course, "classes": classes},
    )


@admin_required
@require_http_methods(["GET", "POST"])
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk)
    form = CourseForm(request.POST or None, instance=course)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "បានរក្សាទុកវគ្គសិក្សា។")
        return redirect("academics:course_list")
    if request.method == "POST" and request.POST.get("from_modal"):
        return _course_list_response(request, form=form, open_form_modal=True)
    return render(
        request,
        "academics/course_form.html",
        {"page_title": f"កែវគ្គ · {course.name}", "form": form, "course": course},
    )


@admin_required
@require_GET
def class_list(request):
    return _class_list_response(request)


@admin_required
@require_http_methods(["GET", "POST"])
def class_create(request):
    initial = {}
    course_id = request.GET.get("course")
    if course_id:
        initial["course"] = course_id
    form = CourseClassForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "បានបង្កើតថ្នាក់រៀន។")
        return redirect("academics:class_list")
    if request.method == "POST" and request.POST.get("from_modal"):
        return _class_list_response(request, form=form, open_form_modal=True)
    return render(
        request,
        "academics/class_form.html",
        {"page_title": "បន្ថែមថ្នាក់រៀន", "form": form, "course_class": None},
    )


@admin_required
@require_GET
def class_detail(request, pk):
    course_class = get_object_or_404(CourseClass.objects.select_related("course"), pk=pk)
    enrollments = course_class.enrollments.select_related("student").order_by("student__name_kh")
    taken_ids = enrollments.filter(status=Enrollment.Status.ACTIVE).values_list("student_id", flat=True)
    enroll_form = EnrollIntoClassForm()
    enroll_form.fields["student"].queryset = Student.objects.filter(is_active=True).exclude(
        pk__in=taken_ids
    )
    return render(
        request,
        "academics/class_detail.html",
        {
            "page_title": course_class.name,
            "course_class": course_class,
            "enrollments": enrollments,
            "enroll_form": enroll_form,
        },
    )


@admin_required
@require_http_methods(["GET", "POST"])
def class_edit(request, pk):
    course_class = get_object_or_404(CourseClass, pk=pk)
    form = CourseClassForm(request.POST or None, instance=course_class)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "បានរក្សាទុកថ្នាក់រៀន។")
        return redirect("academics:class_list")
    if request.method == "POST" and request.POST.get("from_modal"):
        return _class_list_response(request, form=form, open_form_modal=True)
    return render(
        request,
        "academics/class_form.html",
        {"page_title": f"កែថ្នាក់ · {course_class.name}", "form": form, "course_class": course_class},
    )


@admin_required
@require_POST
def class_enroll(request, pk):
    course_class = get_object_or_404(CourseClass, pk=pk)
    form = EnrollIntoClassForm(request.POST)
    if form.is_valid():
        try:
            enroll_student(
                form.cleaned_data["student"],
                course_class,
                user=request.user,
                note=form.cleaned_data.get("note") or "",
                next_due_date=form.cleaned_data.get("next_due_date"),
            )
            messages.success(request, "បានចុះឈ្មោះសិស្ស។")
        except ValidationError as exc:
            messages.error(request, exc.messages[0] if hasattr(exc, "messages") else str(exc))
    else:
        messages.error(request, "សូមជ្រើសសិស្ស។")
    return redirect(course_class)


@admin_required
@require_POST
def class_delete(request, pk):
    course_class = get_object_or_404(CourseClass, pk=pk)
    if course_class.enrollments.exists():
        messages.error(request, "មិនអាចលុបថ្នាក់ដែលមានប្រវត្តិចុះឈ្មោះ។")
        return redirect("academics:class_list")
    try:
        course_class.delete()
    except ProtectedError:
        messages.error(request, "មិនអាចលុបថ្នាក់នេះបានទេ។")
        return redirect("academics:class_list")
    messages.success(request, "បានលុបថ្នាក់រៀន។")
    return redirect("academics:class_list")


@admin_required
@require_POST
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if course.classes.exists():
        messages.error(request, "មិនអាចលុបវគ្គដែលមានថ្នាក់រៀន។")
        return redirect("academics:course_list")
    course.delete()
    messages.success(request, "បានលុបវគ្គសិក្សា។")
    return redirect("academics:course_list")
