from django.urls import reverse


def format_time(value):
    return value.strftime("%H:%M") if value else ""


def class_payload(course_class):
    return {
        "course": str(course_class.course_id),
        "name": course_class.name,
        "instructor": str(course_class.instructor_id or ""),
        "instructor_name": course_class.instructor_name,
        "start_date": course_class.start_date.isoformat() if course_class.start_date else "",
        "end_date": course_class.end_date.isoformat() if course_class.end_date else "",
        "study_days": [str(day) for day in (course_class.study_days or [])],
        "start_time": format_time(course_class.start_time),
        "end_time": format_time(course_class.end_time),
        "is_active": course_class.is_active,
        "label": course_class.name,
        "edit_url": reverse("academics:class_edit", args=[course_class.pk]),
        "delete_url": reverse("academics:class_delete", args=[course_class.pk]),
    }


def course_payload(course):
    return {
        "name": course.name,
        "name_kh": course.name_kh,
        "description": course.description,
        "fee_type": course.fee_type,
        "default_fee": str(course.default_fee),
        "currency": course.currency,
        "is_active": course.is_active,
        "label": course.name,
        "edit_url": reverse("academics:course_edit", args=[course.pk]),
        "delete_url": reverse("academics:course_delete", args=[course.pk]),
    }
