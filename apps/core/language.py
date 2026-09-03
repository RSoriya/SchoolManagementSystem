from html.parser import HTMLParser
import re

from django.utils.translation import get_language

EN = {
    "ផ្ទាំងគ្រប់គ្រង": "Dashboard",
    "ការគ្រប់គ្រង": "Management",
    "សិស្ស": "Students",
    "វគ្គសិក្សា": "Courses",
    "ថ្នាក់រៀន": "Classes",
    "ការបង់ប្រាក់": "Payments",
    "របាយការណ៍": "Reports",
    "អ្នកប្រើប្រាស់": "Users",
    "ការកំណត់": "Settings",
    "ប្រព័ន្ធ": "System",
    "ចាកចេញ": "Log out",
    "ចូលប្រព័ន្ធ": "Sign in",
    "សូមស្វាគមន៍": "Welcome",
    "ឈ្មោះអ្នកប្រើប្រាស់": "Username",
    "ពាក្យសម្ងាត់": "Password",
    "ចងចាំខ្ញុំ": "Remember me",
    "បញ្ចូលឈ្មោះអ្នកប្រើប្រាស់": "Enter username",
    "បញ្ចូលពាក្យសម្ងាត់": "Enter password",
    "បញ្ចូលព័ត៌មានគណនីរបស់អ្នក ដើម្បីបន្តទៅកាន់ផ្ទាំងគ្រប់គ្រង។": "Enter your account details to continue to the dashboard.",
    "ប្រសិនបើអ្នកមិនអាចចូលបាន សូមទាក់ទងអ្នកគ្រប់គ្រងប្រព័ន្ធ។": "If you cannot sign in, contact the system administrator.",
    "ឈ្មោះអ្នកប្រើប្រាស់ ឬពាក្យសម្ងាត់មិនត្រឹមត្រូវ។": "Username or password is incorrect.",
    "បានព្យាយាមចូលច្រើនដងពេក។ សូមរង់ចាំបន្តិច។": "Too many sign-in attempts. Please wait a moment.",
    "គណនីនេះត្រូវបានផ្អាក។": "This account is suspended.",
    "បង្កើតឡើងសម្រាប់ការងារប្រចាំថ្ងៃ": "Built for daily school work",
    "គ្រប់គ្រងសិស្ស ថ្នាក់រៀន និងការបង់ប្រាក់នៅកន្លែងតែមួយ": "Manage students, classes, and payments in one place",
    "ប្រព័ន្ធសម្រាប់សាលាភាសាអង់គ្លេស និងកុំព្យូទ័រ ដែលផ្តោតលើភាពសាមញ្ញ ត្រឹមត្រូវ និងងាយស្រួលតាមដាន។": "A system for English and computer schools, focused on simplicity and accurate tracking.",
    "ចុះឈ្មោះសិស្ស និងថ្នាក់រៀន": "Enroll students and classes",
    "តាមដានការបង់ថ្លៃសិក្សា USD / KHR": "Track tuition in USD / KHR",
    "បង្កាន់ដៃភាសាខ្មែរ លើក្រដាស A4": "Khmer receipts on A4 paper",
    "ប្រព័ន្ធគ្រប់គ្រងសាលារៀន": "School management system",
    "ប្រព័ន្ធគ្រប់គ្រងសាលាភាសាអង់គ្លេស និងកុំព្យូទ័រ": "School management system for English and computer schools",
    "ការជូនដំណឹង": "Alerts",
    "បើកម៉ឺនុយ": "Open menu",
    "បិទម៉ឺនុយ": "Close menu",
    "ម៉ឺនុយមេ": "Main menu",
    "អ្នកគ្រប់គ្រង": "Admin",
    "អ្នកគិតលុយ": "Cashier",
    "គ្រូបង្រៀន": "Teacher",
    "ស្វែងរក": "Search",
    "សម្អាត": "Clear",
    "ច្រោះ": "Filter",
    "រក្សាទុក": "Save",
    "បោះបង់": "Cancel",
    "បន្ទាប់": "Next",
    "មុន": "Previous",
    "ទំព័រ": "Page",
    "បង្ហាញ": "Showing",
    "ក្នុង": "of",
    "១០ / ទំព័រ": "10 / page",
    "២០ / ទំព័រ": "20 / page",
    "ល.រ": "No.",
    "សកម្មភាព": "Actions",
    "កែ": "Edit",
    "លុប": "Delete",
    "មើល": "View",
    "បិទ": "Close",
    "+ បន្ថែមសិស្ស": "+ Add student",
    "+ បន្ថែមវគ្គ": "+ Add course",
    "+ បន្ថែមថ្នាក់": "+ Add class",
    "+ ចុះឈ្មោះសិស្ស": "+ Enroll student",
    "+ ទទួលបង់ប្រាក់": "+ Collect payment",
    "+ បន្ថែមវិធីបង់": "+ Add method",
    "បន្ថែមសិស្ស": "Add student",
    "បន្ថែមវគ្គសិក្សា": "Add course",
    "បន្ថែមថ្នាក់រៀន": "Add class",
    "បន្ថែមអ្នកប្រើ": "Add user",
    "កែព័ត៌មានសិស្ស": "Edit student",
    "កែព័ត៌មាន": "Edit details",
    "កែវគ្គសិក្សា": "Edit course",
    "កែថ្នាក់រៀន": "Edit class",
    "កែថ្នាក់": "Edit class",
    "កែវគ្គ": "Edit course",
    "កែអ្នកប្រើប្រាស់": "Edit user",
    "ស្វែងរក លេខសម្គាល់ ឈ្មោះ ឬទូរសព្ទ": "Search ID, name, or phone",
    "ស្វែងរកវគ្គសិក្សា": "Search courses",
    "ស្វែងរកថ្នាក់ ឬគ្រូ": "Search class or teacher",
    "ស្វែងរក បង្កាន់ដៃ សិស្ស ឬថ្នាក់": "Search receipt, student, or class",
    "ស្វែងរកលេខបង្កាន់ដៃ ឬសិស្ស": "Search receipt number or student",
    "ស្វែងរក សកម្មភាព អ្នកប្រើ ឬវត្ថុ": "Search action, user, or object",
    "ស្វែងរក ឈ្មោះ ឬទូរសព្ទ": "Search name or phone",
    "គ្រប់ថ្នាក់": "All classes",
    "គ្រប់វគ្គ": "All courses",
    "គ្រប់ស្ថានភាព": "All statuses",
    "គ្រប់សកម្មភាព": "All actions",
    "លេខសម្គាល់": "ID",
    "ទូរសព្ទ": "Phone",
    "ភេទ": "Gender",
    "ស្ថានភាព": "Status",
    "សកម្ម": "Active",
    "ផ្អាកគណនី": "Suspended",
    "ប្រុស": "Male",
    "ស្រី": "Female",
    "ឈ្មោះ": "Name",
    "ថ្ងៃកំណើត": "Date of birth",
    "អ៊ីមែល": "Email",
    "អាសយដ្ឋាន": "Address",
    "អាណាព្យាបាល": "Guardian",
    "ព័ត៌មានទំនាក់ទំនង": "Contact details",
    "ព័ត៌មានសិស្ស": "Student details",
    "ព័ត៌មានអាណាព្យាបាល": "Guardian details",
    "ឈ្មោះជាភាសាខ្មែរ": "Khmer name",
    "ឈ្មោះជាភាសាអង់គ្លេស": "English name",
    "ថ្ងៃខែឆ្នាំកំណើត": "Date of birth",
    "លេខទូរសព្ទ": "Phone number",
    "ឈ្មោះអាណាព្យាបាល": "Guardian name",
    "ទូរសព្ទអាណាព្យាបាល": "Guardian phone",
    "សិស្សសកម្ម": "Active student",
    "លុបសិស្ស": "Delete student",
    "រូបថត": "Photo",
    "តំណាង": "Relationship",
    "កំណត់ចំណាំ": "Notes",
    "ឪពុក": "Father",
    "ម្ដាយ": "Mother",
    "ផ្សេងៗ": "Other",
    "ប្រវត្តិចុះឈ្មោះ": "Enrollment history",
    "ថ្ងៃចុះឈ្មោះ": "Enrolled on",
    "ថ្ងៃផុតកំណត់": "Due date",
    "ថ្ងៃផុតកំណត់បន្ទាប់": "Next due date",
    "ថ្ងៃផុតកំណត់បច្ចុប្បន្ន": "Current due date",
    "នៅជំពាក់": "Remaining",
    "ទទួលបង់": "Collect",
    "ទទួលបង់ប្រាក់": "Collect payment",
    "ផ្ទេរ": "Transfer",
    "ផ្អាក": "Suspend",
    "បញ្ចប់": "Complete",
    "បោះបង់": "Cancel",
    "ចុះឈ្មោះសិស្ស": "Enroll student",
    "ចុះឈ្មោះ": "Enroll",
    "មិនមានសិស្សត្រូវនឹងការស្វែងរក។": "No students match this search.",
    "មិនទាន់មានសិស្ស។": "No students yet.",
    "មិនទាន់មានវគ្គសិក្សា។": "No courses yet.",
    "មិនទាន់មានថ្នាក់រៀន។": "No classes yet.",
    "មិនទាន់មានថ្នាក់។": "No classes yet.",
    "មិនទាន់មានការបង់ប្រាក់។": "No payments yet.",
    "មិនទាន់មានបង្កាន់ដៃ។": "No receipts yet.",
    "មិនទាន់មានប្រវត្តិចុះឈ្មោះ។": "No enrollment history yet.",
    "មិនទាន់មានសិស្សជំពាក់។": "No outstanding balances.",
    "មិនមានអ្នកប្រើ។": "No users.",
    "មិនទាន់មាន Audit Log។": "No audit log yet.",
    "មិនមានទិន្នន័យ។": "No data.",
    "មិនមានទិន្នន័យត្រូវនឹងតម្រង។": "No data matches these filters.",
    "នាក់": "students",
    "ជម្រាបសួរ": "Hello",
    "ស្វាគមន៍មកកាន់": "Welcome to",
    "ផ្ទាំងគ្រប់គ្រងស្ថានភាពសិស្ស ថ្នាក់រៀន និងការបង់ថ្លៃសិក្សាប្រចាំថ្ងៃ។": "A daily snapshot of students, classes, and tuition.",
    "ចំនួនសិស្សសរុប": "Total students",
    "កំពុងរៀន": "enrolled",
    "ប្រាក់ចំណូលថ្ងៃនេះ": "Revenue today",
    "ប្រាក់ចំណូលខែនេះ": "Revenue this month",
    "ចំណូលថ្ងៃនេះ": "Revenue today",
    "ចំណូលខែនេះ": "Revenue this month",
    "ចំណូលឆ្នាំនេះ": "Revenue this year",
    "ឆ្នាំនេះ": "this year",
    "ខែនេះ": "this month",
    "ថ្ងៃនេះ": "Today",
    "សិស្សមិនទាន់បង់": "Unpaid students",
    "សិស្សបានបង់": "Paid students",
    "ហួសថ្ងៃផុតកំណត់": "Overdue",
    "ជិតដល់ថ្ងៃផុតកំណត់": "Due soon",
    "ជិតដល់": "due soon",
    "ហួស": "Overdue",
    "ការជូនដំណឹងថ្ងៃផុតកំណត់": "Due date alerts",
    "មិនមានសិស្សហួសថ្ងៃផុតកំណត់។": "No overdue students.",
    "មិនមានសិស្សជិតដល់ថ្ងៃផុតកំណត់។": "No students due soon.",
    "វគ្គសិក្សាសកម្ម": "Active courses",
    "ថ្នាក់រៀនសកម្ម": "Active classes",
    "មើលវគ្គ": "View courses",
    "មើលថ្នាក់": "View classes",
    "មើលទាំងអស់": "View all",
    "គ្រប់ថ្នាក់ →": "All classes →",
    "មើលវគ្គ →": "View courses →",
    "មើលថ្នាក់ →": "View classes →",
    "មើលទាំងអស់ →": "View all →",
    "របាយការណ៍ →": "Reports →",
    "មើល →": "View →",
    "ថ្នាក់សិក្សាថ្ងៃនេះ": "Classes today",
    "ចុះវត្តមានតាមថ្នាក់ដែលមានថ្ងៃសិក្សាថ្ងៃនេះ": "Mark attendance for classes that meet today",
    "បានចុះ": "Marked",
    "មិនទាន់ចុះ": "Not marked",
    "ចុះវត្តមាន": "Attendance",
    "មិនមានថ្នាក់សិក្សាថ្ងៃនេះ។": "No classes today.",
    "ប្រវត្តិចុះឈ្មោះថ្មីៗ": "Recent enrollments",
    "សិស្សដែលបានចូលថ្នាក់ចុងក្រោយ": "Latest students placed in a class",
    "មិនទាន់មានការចុះឈ្មោះ។": "No enrollments yet.",
    "ចំនួនសិស្សតាមវគ្គ": "Students by course",
    "បន្ថែមវគ្គសិក្សា ដើម្បីមើលចំនួនសិស្ស។": "Add a course to see student counts.",
    "ការបង់ថ្មីៗ": "Recent payments",
    "បង្កាន់ដៃដែលបានចេញចុងក្រោយ": "Latest issued receipts",
    "បង់": "Pay",
    "បង្កាន់ដៃ": "Receipt",
    "សរុប": "Total",
    "ថ្នាក់": "Class",
    "វគ្គ": "Course",
    "គ្រូ": "Teacher",
    "ប្រភេទថ្លៃ": "Fee type",
    "ថ្លៃសិក្សា": "Tuition",
    "ប្រចាំខែ": "Monthly",
    "គិតតាមវគ្គ": "Per course",
    "មួយលើក": "One-time",
    "កំពុងប្រើ": "Active",
    "វត្តមាន": "Present",
    "យឺត": "Late",
    "សុំច្បាប់": "Excused",
    "អវត្តមាន": "Absent",
    "ពិន្ទុ": "Scores",
    "លទ្ធផល": "Results",
    "និទ្ទេស": "Grade",
    "មធ្យម": "Average",
    "សរុបពិន្ទុ": "Total score",
    "រក្សាទុកវត្តមាន": "Save attendance",
    "រក្សាទុកពិន្ទុ": "Save scores",
    "បង្កើតប្រឡង": "Create exam",
    "ប្រឡង": "Exam",
    "ពិន្ទុពេញ": "Max score",
    "ចុះតាមថ្ងៃ": "By day",
    "តាមការប្រឡង": "By exam",
    "សិស្សក្នុងថ្នាក់": "Students in class",
    "សិស្សកំពុងរៀន": "Students enrolled",
    "ចុះវត្តមានសិស្សក្នុងថ្នាក់នេះ": "Mark attendance for this class",
    "ដាក់ពិន្ទុសិស្សតាមការប្រឡង": "Enter exam scores",
    "សរុប · មធ្យម · និទ្ទេស": "Total · average · grade",
    "ថ្ងៃនេះបានចុះ": "Marked today",
    "ថ្ងៃនេះមិនទាន់ចុះ": "Not marked today",
    "ថ្ងៃនេះមិនមែនថ្ងៃសិក្សា": "Not a study day today",
    "មិនទាន់មានប្រឡង": "No exams yet",
    "មិនទាន់មានប្រឡង។": "No exams yet.",
    "មិនទាន់មានពិន្ទុ": "No scores yet",
    "មិនទាន់មានកំណត់ត្រាវត្តមាន។": "No attendance records yet.",
    "មិនទាន់មានកំណត់ត្រាពិន្ទុ។": "No score records yet.",
    "មិនមានសិស្សកំពុងរៀនក្នុងថ្នាក់នេះ។": "No active students in this class.",
    "ទាញយក PDF": "Download PDF",
    "បោះពុម្ព": "Print",
    "បោះពុម្ពម្ដងទៀត": "Print again",
    "Excel": "Excel",
    "ថ្ងៃសង": "Refunded on",
    "វិធីសង": "Refund method",
    "មូលហេតុ": "Reason",
    "ចំនួន": "Amount",
    "ចុងក្រោយបង់": "Last paid",
    "ចំនួនដង": "Times paid",
    "% វត្តមាន": "% present",
    "សិស្ស/ថ្នាក់": "Student/class",
    "ចំណូលសុទ្ធ USD": "Net USD",
    "ចំណូលសុទ្ធ KHR": "Net KHR",
    "បានបង់ USD": "Paid USD",
    "បានបង់ KHR": "Paid KHR",
    "មិនទាន់កំណត់": "Not set",
    "ស្ថានភាពថ្ងៃ": "Status on",
    "គ្រប់រយៈពេល": "All periods",
    "ឈ្មោះ": "Name",
    "វិធីបង់": "Method",
    "វិធីបង់ប្រាក់": "Payment methods",
    "បានបង់": "Paid",
    "បានលុបចោល": "Voided",
    "បានសងប្រាក់": "Refunded",
    "លុបចោល": "Void",
    "សងប្រាក់": "Refund",
    "សងប្រាក់ពេញ": "Full refund",
    "ផ្នែកខ្លះ": "Partial",
    "លុបចោលការបង់ប្រាក់": "Void payment",
    "លុបចោលបង្កាន់ដៃ": "Void receipt",
    "ទទួលបង់ប្រាក់ និងចេញបង្កាន់ដៃ": "Collect payment and issue receipt",
    "ថ្ងៃផុតកំណត់បច្ចុប្បន្ន៖": "Current due date:",
    "ថ្ងៃផុតកំណត់បន្ទាប់៖": "Next due date:",
    "វគ្គប្រចាំខែ៖ បង់ពេញរួច ប្រព័ន្ធដាក់ថ្ងៃផុតកំណត់បន្ទាប់ស្វ័យ (+១ ខែ)។ បង់ផ្នែកខ្លះ នៅថ្ងៃផុតកំណត់ដដែល។": "Monthly courses: after a full payment the next due date is set automatically (+1 month). Partial payments keep the same due date.",
    "វាយស្វែងរក": "Type to search",
    "វាយស្វែងរក ID ឈ្មោះ ឬថ្នាក់": "Search ID, name, or class",
    "វាយស្វែងរក ID ឬឈ្មោះសិស្ស": "Search student ID or name",
    "មិនឃើញសិស្សត្រូវនឹងការស្វែងរក។": "No matching students.",
    "ពីថ្ងៃ": "From",
    "ដល់ថ្ងៃ": "To",
    "គ្រប់រូបិយប័ណ្ណ": "All currencies",
    "ចំណូល": "Revenue",
    "ការសងប្រាក់": "Refunds",
    "សិស្សហួសថ្ងៃផុតកំណត់": "Overdue students",
    "មើលចំណូលខែនេះ": "View this month's revenue",
    "របាយការណ៍សងប្រាក់": "Refund report",
    "របាយការណ៍វត្តមាន": "Attendance report",
    "បញ្ចុះតម្លៃ និងអាហារូបករ": "Discounts and scholarships",
    "អាហារូបករ": "Scholarship",
    "បញ្ចុះតម្លៃ": "Discount",
    "USD និង KHR បង្ហាញសរុបដាច់ពីគ្នា។ មិនមានបម្លែងអត្រាប្តូរប្រាក់។ ចំណូលសុទ្ធ = ការបង់ − ការសង។": "USD and KHR are shown as separate totals. No currency conversion. Net revenue = payments − refunds.",
    "ព័ត៌មានសាលា": "School details",
    "ព័ត៌មានសាលា · Telegram · Backup": "School details · Telegram · Backup",
    "រក្សាទុកការកំណត់": "Save settings",
    "ឈ្មោះ និងនិមិត្តសញ្ញាបង្ហាញលើបង្កាន់ដៃ និងម៉ឺនុយ។": "The name and logo appear on receipts and the menu.",
    "ផ្ញើទៅ Admin chat តែប៉ុណ្ណោះ។ មិនមាន SMS ឬអ៊ីមែល។": "Sent to the admin chat only. No SMS or email.",
    "លំនាំដើម ៣ ថ្ងៃមុនថ្ងៃត្រូវបង់។": "Default is 3 days before the due date.",
    "ផ្ញើរាល់ថ្ងៃរហូតទាល់តែសិស្សបានបង់។": "Send every day until the student pays.",
    "បើក Bot រួចចុច Start មុន បន្ទាប់មកយក Chat ID។ ផ្ញើទៅ Admin តែប៉ុណ្ណោះ។": "Open the bot, tap Start first, then get the Chat ID. Admin chat only.",
    "បានភ្ជាប់": "Connected",
    "មិនទាន់ភ្ជាប់": "Not connected",
    "មិនទាន់កំណត់": "Not set",
    "មិនទាន់កំណត់ Token។": "Token is not set yet.",
    "Token បានកំណត់រួច។ ទុកចោលប្រសិនបើមិនចង់ផ្លាស់ប្ដូរ។": "A token is already set. Leave blank to keep it.",
    "យក Chat ID": "Get Chat ID",
    "ផ្ញើសារសាកល្បង": "Send test message",
    "ផ្ញើការជូនដំណឹងថ្ងៃផុតកំណត់": "Send due date alerts",
    "វិធីបង់ប្រាក់": "Payment methods",
    "បន្ថែមវិធីបង់ប្រាក់": "Add payment method",
    "កែវិធីបង់ប្រាក់": "Edit payment method",
    "លុបវិធីបង់ប្រាក់": "Delete payment method",
    "កូដ": "Code",
    "ត្រូវការ": "Required",
    "មិនត្រូវការ": "Not required",
    "បម្រុងទុកទិន្នន័យ": "Data backup",
    "ឯកសារ": "File",
    "ពេលវេលា": "Time",
    "ទំហំ": "Size",
    "មិនទាន់មាន backup។": "No backups yet.",
    "មិនទាន់មានវិធីបង់ប្រាក់។": "No payment methods yet.",
    "ប្រវត្តិ Telegram ថ្មីៗ": "Recent Telegram history",
    "បានផ្ញើ": "Sent",
    "បរាជ័យ": "Failed",
    "កំហុស": "Error",
    "ប្រភេទ": "Type",
    "ថ្ងៃ": "Date",
    "មិនទាន់មានការផ្ញើ។": "Nothing sent yet.",
    "តួនាទី": "Role",
    "បញ្ជាក់ពាក្យសម្ងាត់": "Confirm password",
    "Audit Log": "Audit Log",
    "មិនមានសិទ្ធិ": "No access",
    "អ្នកមិនអាចចូលទំព័រនេះបានទេ": "You cannot open this page",
    "តួនាទីរបស់អ្នកមិនអនុញ្ញាតឲ្យមើល ឬកែទំព័រនេះ។ សូមត្រឡប់ទៅផ្ទាំងគ្រប់គ្រង ឬទាក់ទងអ្នកគ្រប់គ្រង។": "Your role cannot view or change this page. Return to the dashboard or contact an administrator.",
    "ត្រឡប់ផ្ទាំងគ្រប់គ្រង": "Back to dashboard",
    "មិនអាចចូលបាន": "Cannot continue",
    "សូមបើកទំព័រចូលឡើងវិញ": "Please reopen the sign-in page",
    "សូមបើកទំព័រឡើងវិញ": "Please refresh the page",
    "iPad/Safari រក្សាទំព័រចាស់។ សូមចុចប៊ូតុងខាងក្រោម រួចចូលម្ដងទៀត។": "iPad/Safari kept an old page. Tap the button below, then sign in again.",
    "កុំប្រើ https។": "Do not use https.",
    "ទៅទំព័រចូល": "Go to sign in",
    "បានបង្កើតសិស្ស": "Created student",
    "រួចរាល់។": ".",
    "បានរក្សាទុកព័ត៌មានសិស្ស។": "Student details saved.",
    "បានលុបសិស្ស។": "Student deleted.",
    "មិនអាចលុបសិស្សដែលមានប្រវត្តិចុះឈ្មោះ។": "Cannot delete a student with enrollment history.",
    "បានផ្ទេរថ្នាក់។ ប្រវត្តិចាស់នៅតែរក្សាទុក។": "Class transferred. The previous record was kept.",
    "បានប្ដូរស្ថានភាពការសិក្សា។": "Enrollment status updated.",
    "សកម្មភាពមិនត្រឹមត្រូវ។": "That action is not valid.",
    "បានបង្កើតវគ្គសិក្សា។": "Course created.",
    "បានរក្សាទុកវគ្គសិក្សា។": "Course saved.",
    "បានបង្កើតថ្នាក់រៀន។": "Class created.",
    "បានរក្សាទុកថ្នាក់រៀន។": "Class saved.",
    "បានចុះឈ្មោះសិស្ស។": "Student enrolled.",
    "សូមជ្រើសសិស្ស។": "Please choose a student.",
    "មិនអាចលុបថ្នាក់ដែលមានប្រវត្តិចុះឈ្មោះ។": "Cannot delete a class with enrollment history.",
    "មិនអាចលុបថ្នាក់នេះបានទេ។": "This class cannot be deleted.",
    "បានលុបថ្នាក់រៀន។": "Class deleted.",
    "មិនអាចលុបវគ្គដែលមានថ្នាក់រៀន។": "Cannot delete a course that has classes.",
    "បានលុបវគ្គសិក្សា។": "Course deleted.",
    "បានទទួលបង់ប្រាក់។ បង្កាន់ដៃ": "Payment received. Receipt",
    "បានលុបចោលការបង់ប្រាក់។ កំណត់ត្រាដើមនៅតែរក្សាទុក។": "Payment voided. The original record was kept.",
    "បានសងប្រាក់ពេញ។ កំណត់ត្រាបង់ដើមនៅតែរក្សាទុក។": "Full refund recorded. The original payment was kept.",
    "សូមបំពេញវិធីសង មូលហេតុ និងថ្ងៃសង។": "Enter the refund method, reason, and date.",
    "បានរក្សាទុកការកំណត់សាលា។": "School settings saved.",
    "បានបន្ថែមវិធីបង់ប្រាក់": "Added payment method",
    "បានកែវិធីបង់ប្រាក់": "Updated payment method",
    "បានលុបវិធីបង់ប្រាក់": "Deleted payment method",
    "មិនអាចលុបវិធីបង់ដែលមានប្រវត្តិបង់ ឬសងប្រាក់។": "Cannot delete a method that has payment or refund history.",
    "មិនអាចលុបវិធីបង់នេះបានទេ។": "This payment method cannot be deleted.",
    "បានយក Chat ID": "Saved Chat ID",
    "សូមចុចផ្ញើសារសាកល្បង។": "Please send a test message.",
    "បានផ្ញើសារសាកល្បងទៅ Admin chat។": "Test message sent to the admin chat.",
    "បានបង្កើតអ្នកប្រើ": "Created user",
    "បានរក្សាទុកអ្នកប្រើប្រាស់។": "User saved.",
    "មិនអាចផ្អាកគណនីនេះបានទេ។": "This account cannot be suspended.",
    "បានផ្អាកគណនី។ ប្រវត្តិនៅតែរក្សាទុក។": "Account suspended. History was kept.",
    "សូមជ្រើស Save as PDF ក្នុងប្រអប់ Print។": "Choose Save as PDF in the print dialog.",
    "សូមដាក់ថ្ងៃដូចគ្នាទាំងពីរ ដើម្បីចុះវត្តមាន។": "Set both dates to the same day to mark attendance.",
    "សូមជ្រើសប្រឡង។": "Please choose an exam.",
    "សូមបំពេញឈ្មោះ និងថ្ងៃប្រឡង។": "Enter the exam name and date.",
    "បានបង្កើតប្រឡង": "Created exam",
    "ជូនដំណឹងមុនថ្ងៃផុតកំណត់ (ថ្ងៃ)": "Remind before due date (days)",
    "ផ្អាកការសិក្សានេះ?": "Suspend this enrollment?",
    "បញ្ចប់ការសិក្សានេះ?": "Complete this enrollment?",
    "បោះបង់ការសិក្សានេះ? ប្រវត្តិនឹងនៅតែរក្សាទុក។": "Drop this enrollment? History will be kept.",
    "បោះបង់ការសិក្សានេះ?": "Drop this enrollment?",
    "តើអ្នកពិតជាចង់លុប": "Do you really want to delete",
    "តើអ្នកពិតជាចង់លុបចោល": "Do you really want to void",
    "តើអ្នកពិតជាចង់ផ្អាក": "Do you really want to suspend",
    "មែនទេ?": "?",
    "កំណត់ត្រាដើមនឹងនៅតែរក្សាទុក។": "The original record will be kept.",
    "បង្កាន់ដៃដើមនឹងនៅតែរក្សាទុក។": "The original receipt will be kept.",
    "ប្រវត្តិនៅតែរក្សាទុក។": "History will be kept.",
    "ថ្ងៃសិក្សា": "Study days",
    "គ្រប់រយៈពេល": "All periods",
    "ស្ថានភាពថ្ងៃ": "Status on",
    "ពី": "From",
    "ដល់": "to",
}

_ATTRS = {
    "placeholder",
    "aria-label",
    "title",
    "alt",
    "data-add-title",
    "data-edit-title",
    "data-form-title",
    "data-combobox-placeholder",
}

_SKIP_TAGS = {"script", "style", "code", "pre", "textarea"}
_PAIRS = tuple(sorted(EN.items(), key=lambda item: len(item[0]), reverse=True))
# Short labels are exact-match only so names like "សិស្ស A" stay unchanged.
_SUBSTRING_PAIRS = tuple((khmer, english) for khmer, english in _PAIRS if len(khmer) >= 8)
_BOUNDED = tuple(
    sorted(
        {
            "នាក់": "students",
            "ហួស": "Overdue",
            "ក្នុង": "of",
            "ជិតដល់": "due soon",
            "ឆ្នាំនេះ": "this year",
            "ខែនេះ": "this month",
            "បង្ហាញ": "Showing",
        }.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )
)
_BOUNDED_RE = tuple(
    (re.compile(rf"(?<![\u1780-\u17ff]){re.escape(khmer)}(?![\u1780-\u17ff])"), english)
    for khmer, english in _BOUNDED
)


def is_english():
    language = (get_language() or "km").replace("_", "-").lower()
    return language.startswith("en")


def tr(text):
    if text is None:
        return text
    source = str(text)
    if not source or not is_english():
        return source
    if not any("\u1780" <= char <= "\u17ff" for char in source):
        return source
    exact = EN.get(source)
    if exact is not None:
        return exact
    leading = source[: len(source) - len(source.lstrip())]
    trailing = source[len(source.rstrip()) :]
    core = source.strip()
    mapped = EN.get(core)
    if mapped is not None:
        return f"{leading}{mapped}{trailing}"
    translated = core
    for khmer, english in _SUBSTRING_PAIRS:
        if khmer in translated:
            translated = translated.replace(khmer, english)
    for pattern, english in _BOUNDED_RE:
        translated = pattern.sub(english, translated)
    return f"{leading}{translated}{trailing}"


class _HtmlTranslator(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts = []
        self.skip = 0
        self.skip_i18n = 0
        self.i18n_stack = []

    def handle_starttag(self, tag, attrs):
        self.parts.append(self._start(tag, attrs, close=False))
        if tag in _SKIP_TAGS:
            self.skip += 1
        if dict(attrs).get("data-no-i18n") is not None:
            self.skip_i18n += 1
            self.i18n_stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.parts.append(self._start(tag, attrs, close=True))

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self.skip:
            self.skip -= 1
        if self.i18n_stack and self.i18n_stack[-1] == tag:
            self.i18n_stack.pop()
            self.skip_i18n = max(0, self.skip_i18n - 1)
        self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        if self.skip or self.skip_i18n:
            self.parts.append(data)
        else:
            self.parts.append(tr(data))

    def handle_entityref(self, name):
        self.parts.append(f"&{name};")

    def handle_charref(self, name):
        self.parts.append(f"&#{name};")

    def handle_comment(self, data):
        self.parts.append(f"<!--{data}-->")

    def handle_decl(self, decl):
        self.parts.append(f"<!{decl}>")

    def unknown_decl(self, data):
        self.parts.append(f"<![{data}]>")

    def _start(self, tag, attrs, *, close):
        skip_attrs = self.skip or self.skip_i18n
        pieces = [f"<{tag}"]
        for name, value in attrs:
            if value is None:
                pieces.append(f" {name}")
                continue
            translated = value if skip_attrs else self._attr(name, value)
            pieces.append(f' {name}="{translated}"')
        pieces.append(" />" if close else ">")
        return "".join(pieces)

    def _attr(self, name, value):
        if name in _ATTRS:
            return tr(value).replace('"', "&quot;")
        if name == "onsubmit" and "confirm(" in value:
            return _translate_confirm(value).replace('"', "&quot;")
        return value.replace('"', "&quot;") if '"' in value else value


def _translate_confirm(value):
    def replacer(match):
        quote = match.group(1)
        return f"confirm({quote}{tr(match.group(2))}{quote})"

    return re.sub(r"confirm\((['\"])(.*?)\1\)", replacer, value)


def translate_html(html):
    if not html or not is_english():
        return html
    parser = _HtmlTranslator()
    parser.feed(html)
    parser.close()
    return "".join(parser.parts)
