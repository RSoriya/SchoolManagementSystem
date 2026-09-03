from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.models import AuditEvent
from apps.audit.services import log_event
from apps.core.language import tr

from .attendance import roster_enrollments
from .models import ScoreRecord

TWOPLACES = Decimal("0.01")

GRADE_LEGEND = (
    ("A", "ល្អប្រសើរ", "៩០–១០០"),
    ("B", "ល្អណាស់", "៨០–៨៩"),
    ("C", "ល្អ", "៧០–៧៩"),
    ("D", "មធ្យម", "៦០–៦៩"),
    ("E", "ខ្សោយ", "៥០–៥៩"),
    ("F", "ធ្លាក់", "ក្រោម ៥០"),
)


def as_percent(score, max_score):
    if score is None or not max_score:
        return None
    return (Decimal(score) * Decimal("100") / Decimal(max_score)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def letter_grade(percent):
    if percent is None:
        return None
    value = Decimal(percent)
    if value >= 90:
        code, label = "A", "ល្អប្រសើរ"
    elif value >= 80:
        code, label = "B", "ល្អណាស់"
    elif value >= 70:
        code, label = "C", "ល្អ"
    elif value >= 60:
        code, label = "D", "មធ្យម"
    elif value >= 50:
        code, label = "E", "ខ្សោយ"
    else:
        code, label = "F", "ធ្លាក់"
    return {"code": code, "label": label, "percent": value}


def error_message(exc):
    if hasattr(exc, "messages") and exc.messages:
        return exc.messages[0]
    return str(exc)


def parse_score(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        score = Decimal(text)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError("ពិន្ទុមិនត្រឹមត្រូវ។") from exc
    return score


def score_sheet_rows(assessment):
    existing = {row.enrollment_id: row for row in assessment.scores.all()}
    rows = []
    for enrollment in roster_enrollments(assessment.course_class):
        record = existing.get(enrollment.pk)
        rows.append(
            {
                "enrollment": enrollment,
                "student": enrollment.student,
                "score": record.score if record else None,
                "record": record,
            }
        )
    return rows


def save_class_scores(assessment, marks, *, user=None):
    roster = {enrollment.pk: enrollment for enrollment in roster_enrollments(assessment.course_class)}
    if not roster:
        raise ValidationError("ថ្នាក់នេះមិនទាន់មានសិស្សកំពុងរៀន។")
    cleaned = {}
    for enrollment_id, raw in marks.items():
        try:
            enrollment_id = int(enrollment_id)
        except (TypeError, ValueError):
            continue
        if enrollment_id not in roster:
            continue
        score = parse_score(raw)
        if score is None:
            continue
        if score < 0:
            raise ValidationError("ពិន្ទុមិនអាចតូចជាង ០។")
        if score > assessment.max_score:
            raise ValidationError("ពិន្ទុលើសពិន្ទុពេញ។")
        cleaned[enrollment_id] = score
    if not cleaned:
        raise ValidationError("សូមដាក់ពិន្ទុសិស្សយ៉ាងតិចម្នាក់។")

    marked_by = user if getattr(user, "is_authenticated", False) else None
    with transaction.atomic():
        for enrollment_id, score in cleaned.items():
            enrollment = roster[enrollment_id]
            ScoreRecord.objects.update_or_create(
                assessment=assessment,
                enrollment=enrollment,
                defaults={
                    "course_class": assessment.course_class,
                    "student": enrollment.student,
                    "score": score,
                    "marked_by": marked_by,
                },
            )
        log_event(
            action=AuditEvent.Action.SCORE_MARKED,
            summary=f"ដាក់ពិន្ទុ {assessment.name} · {assessment.course_class.name} · {len(cleaned)} នាក់",
            user=user,
            obj=assessment.course_class,
            extra={"assessment": assessment.pk, "count": len(cleaned)},
        )
    return len(cleaned)


def student_score_history(student, classes, limit=40):
    rows = []
    records = (
        ScoreRecord.objects.filter(student=student, course_class__in=classes)
        .select_related("assessment", "course_class", "course_class__course")
        .order_by("-assessment__assessed_on", "-pk")[:limit]
    )
    for record in records:
        percent = as_percent(record.score, record.assessment.max_score)
        rows.append(
            {
                "record": record,
                "assessment": record.assessment,
                "course_class": record.course_class,
                "score": record.score,
                "max_score": record.assessment.max_score,
                "percent": percent,
                "grade": letter_grade(percent),
            }
        )
    return rows


def class_result_table(course_class):
    assessments = list(course_class.assessments.order_by("assessed_on", "pk"))
    enrollments = list(roster_enrollments(course_class))
    score_map = {}
    if enrollments:
        for record in ScoreRecord.objects.filter(
            course_class=course_class,
            enrollment__in=enrollments,
        ):
            score_map[(record.enrollment_id, record.assessment_id)] = record.score
    rows = []
    for enrollment in enrollments:
        exam_scores = []
        total = Decimal("0")
        total_max = Decimal("0")
        marked = 0
        for assessment in assessments:
            score = score_map.get((enrollment.pk, assessment.pk))
            exam_scores.append({"assessment": assessment, "score": score})
            if score is not None:
                total += score
                total_max += assessment.max_score
                marked += 1
        percent = as_percent(total, total_max) if marked else None
        rows.append(
            {
                "enrollment": enrollment,
                "student": enrollment.student,
                "exam_scores": exam_scores,
                "total": total if marked else None,
                "total_max": total_max if marked else None,
                "percent": percent,
                "grade": letter_grade(percent),
            }
        )
    return {"assessments": assessments, "rows": rows}


def class_result_export_table(course_class):
    table = class_result_table(course_class)
    headers = [tr("ល.រ"), "ID", tr("ឈ្មោះ"), tr("ភេទ")]
    headers.extend(assessment.name for assessment in table["assessments"])
    headers.extend([tr("សរុប"), tr("មធ្យម"), tr("និទ្ទេស")])
    rows = []
    for index, row in enumerate(table["rows"], start=1):
        student = row["student"]
        name = student.name_kh
        if student.name_en:
            name = f"{student.name_kh} ({student.name_en})"
        cells = [index, student.student_id, name, tr(student.get_gender_display())]
        cells.extend(
            exam["score"] if exam["score"] is not None else "—"
            for exam in row["exam_scores"]
        )
        if row["total"] is not None:
            grade = row["grade"] or {}
            cells.extend(
                [
                    f"{row['total']} / {row['total_max']}",
                    f"{row['percent']}%",
                    f"{grade.get('code', '')} {grade.get('label', '')}".strip() or "—",
                ]
            )
        else:
            cells.extend(["—", "—", "—"])
        rows.append(cells)
    return {
        "assessments": table["assessments"],
        "headers": headers,
        "rows": rows,
        "result_rows": table["rows"],
    }


def score_register(course_class, assessment=None):
    table = class_result_table(course_class)
    for row in table["rows"]:
        current = next(
            (item for item in row["exam_scores"] if assessment and item["assessment"].pk == assessment.pk),
            None,
        )
        row["score"] = current["score"] if current else None
    return table
