# School Management System

English/computer school. V1 is a single-branch Admin portal. Inspired by EduPay workflows, never copy EduPay code.

## Stack

Django modular monolith, HTML templates, Tailwind, PostgreSQL (SQLite allowed locally), cloud deploy later.

## V1 modules

Dashboard, Students, Courses, Classes/Schedule, Enrollments, Payments, Receipts, Reports, Users, Audit Log, Notifications, Settings.

## Out of scope for V1

Google Sheets, switch-role UI, attendance, exams, scores, report cards, multi-branch, teacher/cashier/parent/student roles and portals, payment gateways, SMS/email.

## Hard rules

- Do not overwrite working Phase 1 foundations; extend them.
- Do not hard-delete academic or billing history. Void/cancel/refund must keep the original record.
- No partial payments. No automatic monthly invoices. Admin sets due dates by hand.
- Late fees are manual. Full refunds only in V1.
- USD and KHR are separate totals. No FX conversion in MVP. Fee and payment use the same currency.
- Student IDs: `STU-YYYY-0001`. Receipts: `RCP-YYYY-000001`.
- V1 role is Admin only. Use Django Groups/permissions so more roles can be added later.
- Telegram goes to the admin chat only. Defaults: remind 3 days before due date; overdue daily until paid.
- PostgreSQL backups: daily, keep 30 days, test restore before production deploy.

## Phase order

1. Foundation (done): Django, auth, layout.
2. Students, courses, classes, schedule, enrollment.
3. Payments, receipts.
4. Due-date alerts, Telegram, refund/cancel, audit log.
5. Dashboard metrics, reports, Excel/PDF.
6. Testing, security, backup/restore, cloud (done).
