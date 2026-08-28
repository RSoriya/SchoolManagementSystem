from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .roles import is_school_admin, is_teacher


def visible_classes(user, queryset=None):
    from apps.academics.models import CourseClass

    queryset = CourseClass.objects.all() if queryset is None else queryset
    if is_school_admin(user) or not is_teacher(user):
        return queryset
    return queryset.filter(instructor=user)


def visible_courses(user, queryset=None):
    from apps.academics.models import Course

    queryset = Course.objects.all() if queryset is None else queryset
    if is_school_admin(user) or not is_teacher(user):
        return queryset
    return queryset.filter(classes__instructor=user).distinct()


def visible_students(user, queryset=None):
    from apps.students.models import Student

    queryset = Student.objects.all() if queryset is None else queryset
    if is_school_admin(user) or not is_teacher(user):
        return queryset
    return queryset.filter(enrollments__course_class__instructor=user).distinct()


def visible_enrollments(user, queryset=None):
    from apps.academics.models import Enrollment

    queryset = Enrollment.objects.all() if queryset is None else queryset
    if is_school_admin(user) or not is_teacher(user):
        return queryset
    return queryset.filter(course_class__instructor=user)


def get_visible_class(user, pk):
    return get_object_or_404(visible_classes(user).select_related("course", "instructor"), pk=pk)


def get_visible_student(user, **kwargs):
    return get_object_or_404(visible_students(user), **kwargs)


def teacher_owns_class(user, course_class):
    if is_school_admin(user) or not is_teacher(user):
        return True
    return course_class.instructor_id == user.pk


def assert_teacher_can_view_class(user, course_class):
    if not teacher_owns_class(user, course_class):
        raise PermissionDenied
