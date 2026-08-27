from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.academics.models import Course, CourseClass, Enrollment
from apps.academics.services import enroll_student, set_enrollment_status, transfer_enrollment
from apps.billing.models import Payment
from apps.billing.services import collect_payment, refund_payment, void_payment
from apps.core.models import PaymentMethod
from apps.students.models import Student

DEMO_NOTE = "ទិន្នន័យឧទាហរណ៍"
ZERO = Decimal("0.00")

COURSES = [
    {
        "name": "English Level 1",
        "name_kh": "ភាសាអង់គ្លេស១",
        "fee_type": Course.FeeType.FULL_COURSE,
        "default_fee": Decimal("5.00"),
        "currency": "USD",
        "description": "វគ្គអង់គ្លេសកម្រិតដំបូង",
    },
    {
        "name": "English Level 2",
        "name_kh": "ភាសាអង់គ្លេស២",
        "fee_type": Course.FeeType.FULL_COURSE,
        "default_fee": Decimal("5.00"),
        "currency": "USD",
        "description": "វគ្គអង់គ្លេសកម្រិតពីរ",
    },
    {
        "name": "English Level 3",
        "name_kh": "ភាសាអង់គ្លេស៣",
        "fee_type": Course.FeeType.FULL_COURSE,
        "default_fee": Decimal("5.00"),
        "currency": "USD",
        "description": "វគ្គអង់គ្លេសកម្រិតបី",
    },
    {
        "name": "Basics Computer 1",
        "name_kh": "កុំព្យូទ័រមូលដ្ឋាន១",
        "fee_type": Course.FeeType.MONTHLY,
        "default_fee": Decimal("10.00"),
        "currency": "USD",
        "description": "វគ្គកុំព្យូទ័រមូលដ្ឋាន",
    },
    {
        "name": "Basics Computer 2",
        "name_kh": "កុំព្យូទ័រមូលដ្ឋាន២",
        "fee_type": Course.FeeType.MONTHLY,
        "default_fee": Decimal("10.00"),
        "currency": "USD",
        "description": "វគ្គកុំព្យូទ័របន្ត",
    },
    {
        "name": "Computer for Administration",
        "name_kh": "កុំព្យូទ័ររដ្ឋបាល",
        "fee_type": Course.FeeType.MONTHLY,
        "default_fee": Decimal("10.00"),
        "currency": "USD",
        "description": "វគ្គកុំព្យូទ័រសម្រាប់ការិយាល័យ",
    },
    {
        "name": "Kids English",
        "name_kh": "អង់គ្លេសកុមារ",
        "fee_type": Course.FeeType.MONTHLY,
        "default_fee": Decimal("25.00"),
        "currency": "USD",
        "description": "វគ្គអង់គ្លេសសម្រាប់កុមារ",
    },
    {
        "name": "Typing Khmer",
        "name_kh": "វាយអក្សរខ្មែរ",
        "fee_type": Course.FeeType.MONTHLY,
        "default_fee": Decimal("80000"),
        "currency": "KHR",
        "description": "វគ្គវាយអក្សរ បង់ជា៛",
    },
]

CLASSES = [
    ("English Level 1", "R201", "វុធ សុរិយា", [0, 1, 2, 3, 4], time(11, 0), time(12, 0)),
    ("English Level 2", "R202", "វុធ សុរិយា", [0, 1, 2, 3, 4], time(14, 0), time(15, 0)),
    ("English Level 1", "R203", "សុខ ចន្ទ្រា", [0, 2, 4], time(17, 0), time(18, 30)),
    ("English Level 1", "R204", "លី សុផល", [5, 6], time(8, 0), time(10, 0)),
    ("English Level 2", "R205", "វុធ សុរិយា", [1, 3], time(18, 0), time(19, 30)),
    ("English Level 3", "R301", "សុខ ចន្ទ្រា", [0, 1, 2, 3, 4], time(9, 0), time(10, 30)),
    ("Basics Computer 1", "C101", "ពៅ វិចិត្រ", [0, 2, 4], time(8, 0), time(9, 30)),
    ("Basics Computer 1", "C102", "ពៅ វិចិត្រ", [1, 3], time(17, 30), time(19, 0)),
    ("Basics Computer 2", "C201", "ម៉ៅ សុភា", [5, 6], time(13, 0), time(15, 0)),
    ("Computer for Administration", "A101", "ម៉ៅ សុភា", [0, 2, 4], time(18, 0), time(19, 30)),
    ("Kids English", "K101", "លី សុផល", [5, 6], time(8, 30), time(10, 0)),
    ("Typing Khmer", "T101", "ហេង រស្មី", [1, 3, 5], time(18, 0), time(19, 0)),
]

STUDENTS = [
    ("សុខា", "Sokha", "male", "096700001", "012800001"),
    ("ដារ៉ា", "Dara", "male", "096700002", "012800002"),
    ("សុផល", "Sophea", "female", "096700003", "012800003"),
    ("វិចិត្រ", "Vicheth", "male", "096700004", "012800004"),
    ("រស្មី", "Reaksmey", "female", "096700005", "012800005"),
    ("ចន្ទ្រា", "Chanthra", "female", "096700006", "012800006"),
    ("ពិសី", "Pisey", "female", "096700007", "012800007"),
    ("វណ្ណៈ", "Vanna", "male", "096700008", "012800008"),
    ("សុភា", "Sopha", "female", "096700009", "012800009"),
    ("រតនា", "Rattana", "male", "096700010", "012800010"),
    ("កញ្ញា", "Kanha", "female", "096700011", "012800011"),
    ("បូណា", "Bona", "male", "096700012", "012800012"),
    ("មករា", "Makara", "male", "096700013", "012800013"),
    ("ស្រីពៅ", "Srey Pov", "female", "096700014", "012800014"),
    ("ធារី", "Theary", "female", "096700015", "012800015"),
    ("វុទ្ធី", "Vuthy", "male", "096700016", "012800016"),
    ("នីតា", "Nita", "female", "096700017", "012800017"),
    ("សំណាង", "Samnang", "male", "096700018", "012800018"),
    ("ពេជ្រ", "Pich", "female", "096700019", "012800019"),
    ("អរុណ", "Arun", "male", "096700020", "012800020"),
    ("ចន្ទី", "Chanty", "female", "096700021", "012800021"),
    ("សុវណ្ណា", "Sovanna", "male", "096700022", "012800022"),
    ("ម៉ាលី", "Maly", "female", "096700023", "012800023"),
    ("រិទ្ធ", "Rith", "male", "096700024", "012800024"),
]


class Command(BaseCommand):
    help = "Insert demo school data (students, classes, enrollments, payments). Safe to run more than once."

    def handle(self, *args, **options):
        today = timezone.localdate()
        admin = get_user_model().objects.filter(is_active=True).order_by("pk").first()
        methods = {item.code: item for item in PaymentMethod.objects.all()}
        if not methods.get("cash"):
            self.stderr.write("មិនទាន់មានវិធីបង់ប្រាក់។ សូម migrate សិន។")
            return

        with transaction.atomic():
            courses = self._courses()
            classes = self._classes(courses, today)
            students = self._students(admin, today)
            enrollments = self._enrollments(students, classes, admin, today)
            self._statuses(enrollments, admin)
            created_payments = self._payments(enrollments, methods, admin, today)
            self._void_and_refund(created_payments, methods, admin, today)

        self.stdout.write(
            self.style.SUCCESS(
                "បានបញ្ចូលទិន្នន័យឧទាហរណ៍៖ "
                f"សិស្ស {Student.objects.count()} · "
                f"ថ្នាក់ {CourseClass.objects.count()} · "
                f"ចុះឈ្មោះ {Enrollment.objects.count()} · "
                f"ការបង់ {Payment.objects.count()}"
            )
        )

    def _courses(self):
        by_name = {}
        for item in COURSES:
            course, _created = Course.objects.get_or_create(
                name=item["name"],
                defaults=item,
            )
            by_name[course.name] = course
        for course in Course.objects.all():
            by_name[course.name] = course
        return by_name

    def _classes(self, courses, today):
        by_name = {}
        for course_name, name, instructor, days, start, end in CLASSES:
            course = courses.get(course_name)
            if not course:
                continue
            course_class, _created = CourseClass.objects.get_or_create(
                course=course,
                name=name,
                defaults={
                    "instructor_name": instructor,
                    "start_date": date(today.year, 1, 15),
                    "end_date": date(today.year, 12, 31),
                    "study_days": days,
                    "start_time": start,
                    "end_time": end,
                    "is_active": True,
                },
            )
            by_name[name] = course_class
        for course_class in CourseClass.objects.select_related("course"):
            by_name[course_class.name] = course_class
        return by_name

    def _students(self, admin, today):
        created = []
        for index, (name_kh, name_en, gender, phone, guardian_phone) in enumerate(STUDENTS, start=1):
            student = Student.objects.filter(phone=phone).first()
            if not student:
                student = Student.objects.create(
                    name_kh=name_kh,
                    name_en=name_en,
                    gender=gender,
                    date_of_birth=date(2008 + (index % 8), (index % 12) + 1, 5),
                    phone=phone,
                    email=f"{name_en.lower().replace(' ', '')}@demo.school",
                    address="ភ្នំពេញ",
                    guardian_name=f"ឪពុកម្តាយ {name_kh}",
                    guardian_phone=guardian_phone,
                    guardian_relationship="អាណាព្យាបាល",
                    notes=DEMO_NOTE,
                    is_active=True,
                    created_by=admin,
                )
            created.append(student)
        return created

    def _enroll(self, student, course_class, admin, enrolled_on, due):
        existing = Enrollment.objects.filter(student=student, course_class=course_class).first()
        if existing:
            return existing
        try:
            return enroll_student(
                student,
                course_class,
                user=admin,
                enrolled_on=enrolled_on,
                next_due_date=due,
                note=DEMO_NOTE,
            )
        except ValidationError:
            return Enrollment.objects.filter(student=student, course_class=course_class).first()

    def _enrollments(self, students, classes, admin, today):
        mapping = [
            (0, "R201", today - timedelta(days=80), today - timedelta(days=12)),
            (1, "R201", today - timedelta(days=70), today - timedelta(days=5)),
            (2, "R203", today - timedelta(days=40), today + timedelta(days=3)),
            (3, "R204", today - timedelta(days=20), today + timedelta(days=3)),
            (4, "R202", today - timedelta(days=60), today + timedelta(days=18)),
            (5, "R205", today - timedelta(days=15), today + timedelta(days=3)),
            (6, "R301", today - timedelta(days=50), today + timedelta(days=40)),
            (7, "C101", today - timedelta(days=55), today - timedelta(days=8)),
            (8, "C101", today - timedelta(days=30), today + timedelta(days=10)),
            (9, "C102", today - timedelta(days=25), today - timedelta(days=2)),
            (10, "C201", today - timedelta(days=45), today + timedelta(days=20)),
            (11, "A101", today - timedelta(days=35), today - timedelta(days=1)),
            (12, "K101", today - timedelta(days=28), today + timedelta(days=7)),
            (13, "K101", today - timedelta(days=14), None),
            (14, "T101", today - timedelta(days=40), today - timedelta(days=6)),
            (15, "T101", today - timedelta(days=10), today + timedelta(days=25)),
            (16, "R203", today - timedelta(days=22), today + timedelta(days=12)),
            (17, "C102", today - timedelta(days=18), today + timedelta(days=15)),
            (18, "R201", today - timedelta(days=12), today + timedelta(days=30)),
            (19, "A101", today - timedelta(days=9), today + timedelta(days=21)),
            (20, "R301", today - timedelta(days=33), today - timedelta(days=20)),
            (21, "C201", today - timedelta(days=8), today + timedelta(days=28)),
            (22, "K101", today - timedelta(days=6), today + timedelta(days=24)),
            (23, "T101", today - timedelta(days=4), today + timedelta(days=26)),
            (0, "C101", today - timedelta(days=50), today + timedelta(days=14)),
            (4, "A101", today - timedelta(days=20), today + timedelta(days=9)),
            (7, "R202", today - timedelta(days=40), today + timedelta(days=16)),
        ]
        enrollments = []
        for index, class_name, enrolled_on, due in mapping:
            course_class = classes.get(class_name)
            if not course_class:
                continue
            enrollment = self._enroll(students[index], course_class, admin, enrolled_on, due)
            if enrollment:
                enrollments.append(enrollment)
        return enrollments

    def _enrollment(self, name_en, class_name):
        return Enrollment.objects.filter(
            student__name_en=name_en,
            course_class__name=class_name,
        ).first()

    def _statuses(self, enrollments, admin):
        suspend = self._enrollment("Vicheth", "R204")
        complete = self._enrollment("Kanha", "C201")
        drop = self._enrollment("Chanty", "R301")
        source = self._enrollment("Sovanna", "C201")
        target = CourseClass.objects.filter(name="R203").first()
        if suspend and suspend.status == Enrollment.Status.ACTIVE:
            set_enrollment_status(suspend, Enrollment.Status.SUSPENDED, user=admin, note=DEMO_NOTE)
        if complete and complete.status == Enrollment.Status.ACTIVE:
            set_enrollment_status(complete, Enrollment.Status.COMPLETED, user=admin, note=DEMO_NOTE)
        if drop and drop.status == Enrollment.Status.ACTIVE:
            set_enrollment_status(drop, Enrollment.Status.DROPPED, user=admin, note=DEMO_NOTE)
        if source and target and source.course_class_id != target.pk and source.status == Enrollment.Status.ACTIVE:
            try:
                transfer_enrollment(source, target, user=admin, note=DEMO_NOTE)
            except ValidationError:
                pass

    def _pay(self, enrollment, *, paid_on, method, admin, tuition=None, registration=ZERO, late=ZERO, discount=ZERO, scholarship=ZERO, reference="", next_due=None, label=""):
        if Payment.objects.filter(enrollment=enrollment, note=DEMO_NOTE, paid_on=paid_on).exists():
            return None
        course = enrollment.course_class.course
        amount = tuition if tuition is not None else course.default_fee
        due = next_due
        if course.fee_type == Course.FeeType.MONTHLY and due is None:
            due = paid_on + timedelta(days=30)
        try:
            return collect_payment(
                enrollment=enrollment,
                paid_on=paid_on,
                tuition_amount=amount,
                method=method,
                registration_fee=registration,
                late_fee=late,
                discount_amount=discount,
                scholarship_amount=scholarship,
                transaction_reference=reference,
                period_label=label or course.get_fee_type_display(),
                next_due_date=due,
                note=DEMO_NOTE,
                user=admin,
            )
        except ValidationError:
            return None

    def _payments(self, enrollments, methods, admin, today):
        cash, aba, khqr, wing = methods["cash"], methods["aba"], methods["khqr"], methods["wing"]
        created = []
        plans = [
            (0, today - timedelta(days=40), cash, ZERO, ZERO, ZERO, ZERO, "", "សីហា"),
            (1, today - timedelta(days=25), aba, Decimal("5.00"), ZERO, ZERO, ZERO, "ABA-88001", "សីហា"),
            (4, today - timedelta(days=18), khqr, ZERO, ZERO, Decimal("1.00"), ZERO, "KHQR-22019", ""),
            (6, today - timedelta(days=12), cash, ZERO, ZERO, ZERO, Decimal("1.00"), "", ""),
            (7, today - timedelta(days=22), wing, ZERO, Decimal("2.00"), ZERO, ZERO, "WING-44102", "កក្កដា"),
            (8, today - timedelta(days=5), cash, ZERO, ZERO, ZERO, ZERO, "", "សីហា"),
            (10, today - timedelta(days=15), aba, ZERO, ZERO, ZERO, ZERO, "ABA-88044", "សីហា"),
            (12, today - timedelta(days=8), cash, ZERO, ZERO, ZERO, ZERO, "", "សីហា"),
            (15, today - timedelta(days=3), khqr, ZERO, ZERO, ZERO, ZERO, "KHQR-22991", "សីហា"),
            (16, today - timedelta(days=1), cash, ZERO, ZERO, ZERO, ZERO, "", ""),
            (17, today, aba, ZERO, ZERO, ZERO, ZERO, "ABA-88110", "សីហា"),
            (18, today, cash, ZERO, ZERO, ZERO, ZERO, "", ""),
            (19, today - timedelta(days=2), wing, ZERO, ZERO, ZERO, ZERO, "WING-44900", "សីហា"),
            (21, today - timedelta(days=4), cash, ZERO, ZERO, ZERO, ZERO, "", "សីហា"),
            (23, today - timedelta(days=6), aba, ZERO, ZERO, ZERO, ZERO, "ABA-88221", "សីហា"),
            (24, today - timedelta(days=11), cash, ZERO, ZERO, ZERO, ZERO, "", "សីហា"),
            (25, today - timedelta(days=7), khqr, ZERO, ZERO, ZERO, ZERO, "KHQR-23002", "សីហា"),
            (26, today - timedelta(days=9), cash, ZERO, ZERO, ZERO, ZERO, "", ""),
        ]
        for index, paid_on, method, registration, late, discount, scholarship, reference, label in plans:
            if index >= len(enrollments) or not enrollments[index]:
                continue
            enrollment = enrollments[index]
            if enrollment.status not in (Enrollment.Status.ACTIVE, Enrollment.Status.SUSPENDED):
                continue
            payment = self._pay(
                enrollment,
                paid_on=paid_on,
                method=method,
                admin=admin,
                registration=registration,
                late=late,
                discount=discount,
                scholarship=scholarship,
                reference=reference,
                label=label,
            )
            if payment:
                created.append(payment)
        return created

    def _void_and_refund(self, payments, methods, admin, today):
        if len(payments) >= 2:
            void_target = payments[0]
            if void_target.status == Payment.Status.COMPLETED:
                try:
                    void_payment(void_target, user=admin, reason="បញ្ចូលខុស · ទិន្នន័យឧទាហរណ៍")
                except ValidationError:
                    pass
        if len(payments) >= 4:
            refund_target = payments[3]
            if refund_target.status == Payment.Status.COMPLETED:
                try:
                    refund_payment(
                        refund_target,
                        method=methods["cash"],
                        reason="សិស្សឈប់រៀន · ទិន្នន័យឧទាហរណ៍",
                        refunded_on=today,
                        user=admin,
                    )
                except ValidationError:
                    pass
