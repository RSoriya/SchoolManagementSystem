from django.urls import reverse


def student_payload(student):
    return {
        "name_kh": student.name_kh,
        "name_en": student.name_en,
        "gender": student.gender,
        "date_of_birth": student.date_of_birth.isoformat() if student.date_of_birth else "",
        "phone": student.phone,
        "email": student.email,
        "address": student.address,
        "guardian_name": student.guardian_name,
        "guardian_phone": student.guardian_phone,
        "guardian_relationship": student.guardian_relationship,
        "notes": student.notes,
        "is_active": student.is_active,
        "label": student.display_name,
        "edit_url": reverse("students:edit", args=[student.student_id]),
        "delete_url": reverse("students:delete", args=[student.student_id]),
    }
