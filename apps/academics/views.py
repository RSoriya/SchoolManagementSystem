from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts.permissions import permission_required
from apps.accounts.roles import user_has_perm
from apps.accounts.scoping import get_visible_class, visible_classes, visible_courses
from apps.billing.services import attach_period_balances
from apps.core.pagination import extra_query, paginate, per_page_value
from apps.core.services import get_school_settings
from apps.reports.exporters import excel_response, pdf_response
from apps.students.models import Student

from .attendance import (
    day_counts,
    day_register,
    error_message,
    is_study_day,
    mark_class_attendance,
    parse_date_range,
)
from .forms import AssessmentForm, CourseClassForm, CourseForm, EnrollIntoClassForm
from .models import Assessment, AttendanceRecord, Course, CourseClass, Enrollment
from .payloads import class_payload, course_payload
from .scores import GRADE_LEGEND
from .scores import error_message as score_error_message
from .scores import class_result_export_table, class_result_table, save_class_scores, score_register
from .services import enroll_student


def _class_list_response(request, form=None, open_form_modal=False):
    query = request.GET.get("q", "").strip()
    course_id = request.GET.get("course", "").strip()
    classes = visible_classes(
        request.user,
        CourseClass.objects.select_related("course", "instructor"),
    ).annotate(
        active_students=Count(
            "enrollments",
            filter=Q(enrollments__status=Enrollment.Status.ACTIVE),
        )
    ).order_by("name")
    if query:
        classes = classes.filter(
            Q(name__icontains=query)
            | Q(instructor_name__icontains=query)
            | Q(instructor__full_name_kh__icontains=query)
            | Q(instructor__username__icontains=query)
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
            "courses": visible_courses(request.user, Course.objects.filter(is_active=True)),
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
    courses = visible_courses(
        request.user,
        Course.objects.annotate(class_count=Count("classes")),
    ).order_by("name")
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


@permission_required("academics.view_course")
@require_GET
def course_list(request):
    return _course_list_response(request)


@permission_required("academics.add_course")
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


@permission_required("academics.view_course")
@require_GET
def course_detail(request, pk):
    course = get_object_or_404(visible_courses(request.user), pk=pk)
    classes = visible_classes(request.user, course.classes).annotate(
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


@permission_required("academics.change_course")
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


@permission_required("academics.view_courseclass")
@require_GET
def class_list(request):
    return _class_list_response(request)


@permission_required("academics.add_courseclass")
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


@permission_required("academics.view_courseclass")
@require_GET
def class_detail(request, pk):
    course_class = get_visible_class(request.user, pk)
    today = timezone.localdate()
    can_view_attendance = user_has_perm(request.user, "academics.view_attendancerecord")
    can_view_scores = user_has_perm(request.user, "academics.view_scorerecord")
    date_value = (request.GET.get("date") or "").strip()
    if date_value and can_view_attendance:
        return redirect(f"{course_class.get_attendance_url()}?from={date_value}&to={date_value}")

    enrollments = course_class.enrollments.select_related("student", "course_class__course").order_by("student__name_kh")
    taken_ids = enrollments.filter(status=Enrollment.Status.ACTIVE).values_list("student_id", flat=True)
    enroll_form = EnrollIntoClassForm()
    enroll_form.fields["student"].queryset = Student.objects.filter(is_active=True).exclude(
        pk__in=taken_ids
    )
    today_counts = day_counts(course_class, today) if can_view_attendance else None
    roster = paginate(request, attach_period_balances(enrollments))
    return render(
        request,
        "academics/class_detail.html",
        {
            "page_title": course_class.name,
            "course_class": course_class,
            "enrollments": roster,
            "enroll_form": enroll_form,
            "active_count": enrollments.filter(status=Enrollment.Status.ACTIVE).count(),
            "today_counts": today_counts,
            "marked_today": bool(today_counts and today_counts["total"]),
            "is_study_day_today": is_study_day(course_class, today) if can_view_attendance else False,
            "assessment_count": course_class.assessments.count() if can_view_scores else 0,
            "per_page": per_page_value(request),
            "extra_query": extra_query(request),
        },
    )


@permission_required("academics.view_attendancerecord")
@require_http_methods(["GET", "POST"])
def class_attendance(request, pk):
    course_class = get_visible_class(request.user, pk)
    today = timezone.localdate()
    can_mark = user_has_perm(request.user, "academics.mark_attendance")
    range_source = request.POST if request.method == "POST" else request.GET
    date_from, date_to = parse_date_range(range_source, today)
    is_single_day = date_from == date_to
    attended_on = date_from if is_single_day else None

    if request.method == "POST":
        if not can_mark:
            raise PermissionDenied
        if not is_single_day:
            messages.error(request, "សូមដាក់ថ្ងៃដូចគ្នាទាំងពីរ ដើម្បីចុះវត្តមាន។")
        else:
            marks = {
                key.removeprefix("status_"): value
                for key, value in request.POST.items()
                if key.startswith("status_") and value
            }
            try:
                count = mark_class_attendance(course_class, attended_on, marks, user=request.user)
            except ValidationError as exc:
                messages.error(request, error_message(exc))
            else:
                messages.success(
                    request,
                    f"បានរក្សាទុកវត្តមាន {course_class.name} · {attended_on.strftime('%d/%m/%Y')} · {count} នាក់",
                )
                return redirect(
                    f"{course_class.get_attendance_url()}?{urlencode({
                        'from': date_from.isoformat(),
                        'to': date_to.isoformat(),
                        **({k: request.GET[k] for k in ('per_page', 'page') if request.GET.get(k)}),
                    })}"
                )

    register = day_register(course_class, date_from, date_to)
    attendance_page = paginate(request, register["rows"])
    return render(
        request,
        "academics/class_attendance.html",
        {
            "page_title": f"វត្តមាន · {course_class.name}",
            "course_class": course_class,
            "can_mark": can_mark and register["is_single_day"],
            "attended_on": register["attended_on"],
            "is_study_day": register["is_study_day"],
            "is_single_day": register["is_single_day"],
            "attendance_rows": attendance_page,
            "counts": register["counts"],
            "date_from": register["date_from"],
            "date_to": register["date_to"],
            "summary_label": register["summary_label"],
            "statuses": AttendanceRecord.Status.choices,
            "per_page": per_page_value(request),
            "extra_query": extra_query(request),
        },
    )


def _pick_assessment(assessments, exam_id):
    if not assessments:
        return None
    if exam_id:
        for item in assessments:
            if str(item.pk) == str(exam_id):
                return item
        return None
    return assessments[0]


def _scores_query(request, assessment=None):
    params = {}
    if assessment:
        params["exam"] = str(assessment.pk)
    for key in ("per_page", "page"):
        if request.GET.get(key):
            params[key] = request.GET[key]
    return urlencode(params)


@permission_required("academics.view_scorerecord")
@require_http_methods(["GET", "POST"])
def class_scores(request, pk):
    course_class = get_visible_class(request.user, pk)
    can_add = user_has_perm(request.user, "academics.add_assessment")
    can_mark = user_has_perm(request.user, "academics.mark_score")
    assessments = list(course_class.assessments.order_by("-assessed_on", "-pk"))
    form = AssessmentForm()
    open_form_modal = False

    if request.method == "POST" and any(key.startswith("score_") for key in request.POST):
        if not can_mark:
            raise PermissionDenied
        assessment = _pick_assessment(assessments, request.POST.get("exam") or request.GET.get("exam"))
        if not assessment:
            messages.error(request, "សូមជ្រើសប្រឡង។")
        else:
            marks = {
                key.removeprefix("score_"): value
                for key, value in request.POST.items()
                if key.startswith("score_")
            }
            try:
                count = save_class_scores(assessment, marks, user=request.user)
            except ValidationError as exc:
                messages.error(request, score_error_message(exc))
            else:
                messages.success(
                    request,
                    f"បានរក្សាទុកពិន្ទុ {assessment.name} · {count} នាក់",
                )
                query = _scores_query(request, assessment)
                return redirect(f"{course_class.get_scores_url()}?{query}" if query else course_class.get_scores_url())
    elif request.method == "POST":
        if not can_add:
            raise PermissionDenied
        open_form_modal = True
        form = AssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.course_class = course_class
            assessment.created_by = request.user
            try:
                assessment.full_clean()
                assessment.save()
            except ValidationError as exc:
                messages.error(request, score_error_message(exc))
            else:
                messages.success(request, f"បានបង្កើតប្រឡង {assessment.name}។")
                return redirect(assessment)
        else:
            messages.error(request, "សូមបំពេញឈ្មោះ និងថ្ងៃប្រឡង។")

    exam_id = request.GET.get("exam")
    if exam_id:
        assessment = get_object_or_404(Assessment, pk=exam_id, course_class=course_class)
    else:
        assessment = assessments[0] if assessments else None
    table = score_register(course_class, assessment)
    score_page = paginate(request, table["rows"])
    marked_count = sum(1 for row in table["rows"] if row.get("score") is not None) if assessment else 0
    return render(
        request,
        "academics/class_scores.html",
        {
            "page_title": f"ពិន្ទុ · {course_class.name}",
            "course_class": course_class,
            "form": form,
            "assessments": assessments,
            "assessment": assessment,
            "score_rows": score_page,
            "can_add": can_add,
            "can_mark": can_mark and assessment is not None,
            "open_form_modal": open_form_modal,
            "marked_count": marked_count,
            "active_count": len(table["rows"]),
            "per_page": per_page_value(request),
            "extra_query": extra_query(request),
        },
    )


def _class_results_export_context(request, pk):
    course_class = get_visible_class(request.user, pk)
    table = class_result_export_table(course_class)
    school = get_school_settings()
    return {
        "course_class": course_class,
        "school": school,
        "page_title": f"លទ្ធផល · {course_class.name}",
        "subtitle": f"{school.school_name} · {course_class.course.name}",
        "headers": table["headers"],
        "table": table["rows"],
        "assessments": table["assessments"],
        "grade_legend": GRADE_LEGEND,
        "print_url": course_class.get_results_url() + "?print=1",
    }


@permission_required("academics.view_scorerecord")
@require_GET
def class_results(request, pk):
    course_class = get_visible_class(request.user, pk)
    table = class_result_table(course_class)
    result_page = paginate(request, table["rows"])
    return render(
        request,
        "academics/class_results.html",
        {
            "page_title": f"លទ្ធផល · {course_class.name}",
            "course_class": course_class,
            "assessments": table["assessments"],
            "result_rows": result_page,
            "grade_legend": GRADE_LEGEND,
            "school": get_school_settings(),
            "per_page": per_page_value(request),
            "extra_query": extra_query(request),
            "open_print": request.GET.get("print") == "1",
        },
    )


@permission_required("academics.view_scorerecord")
@require_GET
def class_results_excel(request, pk):
    context = _class_results_export_context(request, pk)
    course_class = context["course_class"]
    filename = f"results-{course_class.pk}-{timezone.localdate().isoformat()}.xlsx"
    return excel_response(
        filename,
        [
            {
                "title": "លទ្ធផល",
                "heading": context["page_title"],
                "subtitle": context["subtitle"],
                "headers": context["headers"],
                "rows": context["table"],
            }
        ],
    )


@permission_required("academics.view_scorerecord")
@require_GET
def class_results_pdf(request, pk):
    context = _class_results_export_context(request, pk)
    course_class = context["course_class"]
    filename = f"results-{course_class.pk}-{timezone.localdate().isoformat()}.pdf"
    response = pdf_response(request, "academics/class_results_print.html", context, filename)
    if response:
        return response
    messages.info(request, "សូមជ្រើស Save as PDF ក្នុងប្រអប់ Print។")
    return redirect(context["print_url"])


@permission_required("academics.view_scorerecord")
@require_http_methods(["GET", "POST"])
def class_score_sheet(request, pk, assessment_pk):
    course_class = get_visible_class(request.user, pk)
    assessment = get_object_or_404(
        Assessment,
        pk=assessment_pk,
        course_class=course_class,
    )
    if request.method == "POST":
        if not user_has_perm(request.user, "academics.mark_score"):
            raise PermissionDenied
        marks = {
            key.removeprefix("score_"): value
            for key, value in request.POST.items()
            if key.startswith("score_")
        }
        try:
            count = save_class_scores(assessment, marks, user=request.user)
        except ValidationError as exc:
            messages.error(request, score_error_message(exc))
        else:
            messages.success(
                request,
                f"បានរក្សាទុកពិន្ទុ {assessment.name} · {count} នាក់",
            )
        query = _scores_query(request, assessment)
        return redirect(f"{course_class.get_scores_url()}?{query}" if query else course_class.get_scores_url())
    params = request.GET.copy()
    params["exam"] = str(assessment.pk)
    return redirect(f"{course_class.get_scores_url()}?{params.urlencode()}")


@permission_required("academics.change_courseclass")
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


@permission_required("students.enroll_student")
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


@permission_required("academics.delete_courseclass")
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


@permission_required("academics.delete_course")
@require_POST
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if course.classes.exists():
        messages.error(request, "មិនអាចលុបវគ្គដែលមានថ្នាក់រៀន។")
        return redirect("academics:course_list")
    course.delete()
    messages.success(request, "បានលុបវគ្គសិក្សា។")
    return redirect("academics:course_list")
