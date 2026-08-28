# School Management System

English/computer school. V1 is a single-branch Admin portal. Inspired by EduPay workflows, never copy EduPay code.

## Stack

Django modular monolith, HTML templates, Tailwind, PostgreSQL (SQLite allowed locally), cloud deploy later.

## V1 modules

Dashboard, Students, Courses, Classes/Schedule, Enrollments, Payments, Receipts, Reports, Users, Audit Log, Notifications, Settings.

## Out of scope for V1

Google Sheets, switch-role UI, report cards, multi-branch, parent/student portals, payment gateways, SMS/email.

V2 Phase 1 (done): Cashier and Teacher staff roles in the Admin portal. Still no parent/student portals.
V2 Phase 2A (done): After a monthly payment, next due date defaults to +1 calendar month (editable). No auto invoices.
V2 Phase 2B (done): Partial payments. Remaining balance is tracked per period. Due date advances only when the period is paid in full. Full refunds only.
V2 Phase 3 (done): Class page is a hub. Click **វត្តមាន** for a day register (serial, student ID, name, gender, one date dropdown: present / late / excused / absent, totals for a chosen date range at the end); click **ពិន្ទុ** to enter exam scores; click **លទ្ធផល** to view totals, average, and grades (និទ្ទេស) for the class course. Teacher uses own classes (`CourseClass.instructor`); Admin all; Cashier cannot view or mark. Edit allowed; never hard-delete attendance or score history. No standalone attendance menu. No report cards.

## Hard rules

- Do not overwrite working Phase 1 foundations; extend them.
- Do not hard-delete academic or billing history. Void/cancel/refund must keep the original record.
- Partial payments allowed. Remaining balance is tracked per period. After a monthly period is paid in full, next due date defaults to +1 calendar month (editable). No automatic monthly invoices.
- Late fees are manual. Full refunds only in V1.
- USD and KHR are separate totals. No FX conversion in MVP. Fee and payment use the same currency.
- Student IDs: `STU-YYYY-0001`. Receipts: `RCP-YYYY-000001`.
- V1 role is Admin only. V2 Phase 1 adds Cashier and Teacher in the same portal via Django Groups. No parent/student portals.
- Telegram goes to the admin chat only. Defaults: remind 3 days before due date; overdue daily until paid.
- PostgreSQL backups: daily, keep 30 days, test restore before production deploy.

## Phase order

1. Foundation (done): Django, auth, layout.
2. Students, courses, classes, schedule, enrollment.
3. Payments, receipts.
4. Due-date alerts, Telegram, refund/cancel, audit log.
5. Dashboard metrics, reports, Excel/PDF.
6. Testing, security, backup/restore, cloud (done).
