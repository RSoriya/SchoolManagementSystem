# ផែនការ DigitalOcean៖ ប្រព័ន្ធដាច់ដោយឡែកតាមសាលា

កាលបរិច្ឆេទ៖ 2026-09-05

អ្នកបានជ្រើសរើសវិធីទី 1៖ ប្រើ code repository តែមួយ និងដាក់ប្រព័ន្ធដាច់ដោយឡែកសម្រាប់សាលាអតិថិជននីមួយៗ។ ឯកសារនេះកត់ត្រាជម្រើស និងជំហានត្រៀមប្រើប្រាស់; វាមិនមែនជាការបញ្ជាក់ថា production បាន deploy រួចទេ។

## 1. អ្វីដែលសាលានីមួយៗត្រូវមាន

- App Platform app របស់ខ្លួន។
- PostgreSQL database និង database user ដាច់ដោយឡែក ដែលមានសិទ្ធិត្រឹម database របស់សាលានោះ។ កុំប្រើគណនី database admin រួមក្នុង app របស់គ្រប់សាលា។
- URL របស់ខ្លួន; អាចចាប់ផ្ដើមដោយ URL របស់ App Platform ហើយបន្ថែម subdomain ផ្ទាល់ខ្លួនក្រោយមក។
- `SECRET_KEY` និង production secrets ផ្ទាល់ខ្លួន។
- Private storage សម្រាប់រូបថត និង backup ជាមួយ credentials ដែលកំណត់សិទ្ធិសម្រាប់សាលានោះ។ ឈ្មោះ folder ផ្សេងគ្នាតែមួយមុខមិនមែនជាការការពារសិទ្ធិទេ។
- Admin/Cashier/Teacher, School Settings, logo និង Telegram admin chat របស់ខ្លួន។
- កាលវិភាគ backup/reminders និងកំណត់ត្រា restore របស់ខ្លួន។

លេខសិស្ស `STU-YYYY-0001` និងលេខបង្កាន់ដៃ `RCP-YYYY-000001` អាចចាប់ផ្ដើមរៀងៗខ្លួននៅ database របស់សាលានីមួយៗ។ នៅក្នុងបញ្ជីគ្រប់គ្រងរបស់ម្ចាស់សេវា ត្រូវភ្ជាប់លេខទាំងនេះជាមួយ school code ដើម្បីកុំឲ្យច្រឡំ។

ជម្រើសថ្លៃ Hosting ដែលនៅត្រូវសម្រេច៖ database cluster ផ្ទាល់ខ្លួនតាមសាលា ឬ database ដាច់ដោយឡែកក្នុង cluster រួម។ Cluster រួមត្រូវសាកសិទ្ធិបំបែក database ឲ្យបានត្រឹមត្រូវ ហើយការប្រើប្រាស់ធនធាន/ការដាច់សេវាអាចប៉ះពាល់ច្រើនសាលា។ មិនទាន់បានជ្រើសទំហំ ឬបង្កើតធនធានបង់ប្រាក់ទេ។

## 2. មូលដ្ឋានបច្ចុប្បន្ន និងការងារត្រូវបំពេញ

Code បច្ចុប្បន្នសមស្របនឹងមួយសាលាក្នុងមួយការដំឡើង៖ School Settings មានតែមួយ ហើយ Admin/Cashier មើលទិន្នន័យក្នុង database របស់ការដំឡើងនោះ។ កុំបញ្ចូលសាលាអតិថិជនពីរក្នុង database បច្ចុប្បន្នតែមួយ។

លទ្ធផលដែលបានកត់ត្រាក្នុង session មុន៖ tests 130/130 ឆ្លងដោយប្រើ PostgreSQL 16.15។ Backup tests ខ្លះប្ដូរទៅ SQLite ដូច្នេះមិនជំនួសការសាក restore PostgreSQL ពិតទេ។

ការងារមុន deploy សាលាដំបូង៖

- [ ] បង្កើត app spec គំរូដែលអាចបំពេញតាមសាលា ដោយគ្មាន secrets ក្នុង repository។
- [ ] រៀបចំ production settings, domain/CSRF, database SSL និងការអាន secrets នៅ runtime។
- [ ] រៀបចំ healthcheck សម្រាប់ App Platform និងការប្រើ HTTPS ក្រោយ proxy។
- [ ] រៀបចំ build CSS/static files និង deployment job សម្រាប់ migrations មុន web service ចាប់ផ្ដើមប្រើកំណែថ្មី។
- [ ] បំពេញ migrations ដែលនៅខ្វះក្នុង models។
- [ ] កែ login throttling ឲ្យមានប្រសិទ្ធភាពរវាង workers និងផ្ទៀងផ្ទាត់ប្រភព forwarded IP។
- [ ] បន្ថែម storage backend សម្រាប់រូបថត និងសាកសិទ្ធិចូលប្រើ។
- [ ] កែ PostgreSQL client version ឲ្យសមនឹង database server; backup/restore ត្រូវប្រើការភ្ជាប់ SSL ដូច database connection។
- [ ] កែ backup workflow ឲ្យ upload ទៅ private object storage, verify និងរក្សា 30 ថ្ងៃ។ ទំព័របង្ហាញ backup ត្រូវអានបញ្ជីពីទីតាំងដែលរក្សាទុកជាក់ស្ដែង។
- [ ] រៀបចំ scheduled jobs សម្រាប់ backup និង Telegram reminders ព្រមទាំងការតាមដានការបរាជ័យ។

App Platform local filesystem មិនរក្សាទិន្នន័យឆ្លងកាត់ការប្ដូរ container ហើយមិនគាំទ្រ volumes ទេ។ ដូច្នេះ volumes ក្នុង `docker-compose.yml` សម្រាប់ local Docker មិនអាចប្រើជាដំណោះស្រាយរក្សាទុករូបថត/backup នៅ App Platform បានទេ។ [DigitalOcean storage limits](https://docs.digitalocean.com/products/app-platform/details/limits/)

App Platform គាំទ្រ deployment jobs និង scheduled jobs។ កំណត់ timezone របស់សាលាឲ្យច្បាស់ ហើយរក្សា Telegram reminders ទៅ admin chat របស់សាលានោះតែប៉ុណ្ណោះ។ [DigitalOcean jobs](https://docs.digitalocean.com/products/app-platform/how-to/manage-jobs/)

## 3. ជំហានដាក់សាលាថ្មី

1. កត់ត្រា school code, ឈ្មោះសាលា, អ្នកទំនាក់ទំនង, URL, កញ្ចប់សេវា និងថ្ងៃចាប់ផ្ដើម។ ជ្រើស school code ស្ថិរភាពសម្រាប់ការកំណត់ឈ្មោះធនធាន។
2. គណនាថ្លៃ App, PostgreSQL, storage, jobs និងការថែទាំ មុនបង្កើតធនធានបង់ប្រាក់។
3. បង្កើត database/storage/secrets ថ្មី និងកំណត់ app របស់សាលានោះពី code release ដែលបានសាកល្បង។
4. ពិនិត្យ connections របស់ web និង jobs ថាចង្អុលទៅធនធានសាលាត្រឹមត្រូវ មុន migrate ឬ import ទិន្នន័យ។
5. បង្កើត Admin របស់សាលា និង School Settings។ Production ត្រូវចាប់ផ្ដើមពី database ទទេដែលបាន migrate ឬទិន្នន័យរបស់សាលានោះដែលបានផ្ទៀងផ្ទាត់; កុំចម្លង database របស់សាលាផ្សេង។
6. ប្រើទិន្នន័យសាកល្បងដើម្បីសាក students, enrollments, partial payments, refunds, receipts, attendance/scores និងសិទ្ធិ staff។ សាក upload រូបថត និងបង្ហាញឡើងវិញក្រោយ redeploy។
7. សាក backup និង restore ទៅ database ដាច់ដោយឡែក។ ពិនិត្យភាពត្រឹមត្រូវនៃចំនួន records, បង្កាន់ដៃ, សមតុល្យការបង់ប្រាក់ និងរូបថត មុនប្រគល់សេវា។
8. ពិនិត្យថា login/credentials/URLs របស់សាលាមួយមិនផ្ដល់សិទ្ធិចូល app, database ឬ private files របស់សាលាផ្សេង។
9. បើកដំណើរការសាលា និងកត់ត្រា app ID, database/storage identifiers, code version និងថ្ងៃ restore test ចុងក្រោយ។ កត់តែទីតាំងរក្សា secrets ក្នុងបញ្ជីគ្រប់គ្រង; កុំកត់តម្លៃ secrets ក្នុង repository។

បើប្រើ Clone App៖ DigitalOcean ចម្លង database configuration ពី app ដើម។ ត្រូវប្ដូរការភ្ជាប់ database/storage និង Telegram settings របស់ web/jobs មុន deploy សាលាថ្មី។ ពិនិត្យ School Settings ក្នុង database ផង ព្រោះ Telegram settings នៅទីនោះអាច override environment variables។ [DigitalOcean clone documentation](https://docs.digitalocean.com/products/app-platform/how-to/clone-app/)

## 4. ការគ្រប់គ្រងអតិថិជន និងការអាប់ដេត

ម្ចាស់សេវាគ្រប់គ្រងបញ្ជីសាលា ថ្លៃសេវា កាលបរិច្ឆេទបន្តសេវា code version និងស្ថានភាព backup។ ការបង់ថ្លៃសេវារបស់សាលាមកម្ចាស់ប្រព័ន្ធត្រូវកត់ដាច់ដោយឡែកពីការបង់ថ្លៃសិក្សារបស់សិស្ស។ Owner Portal មិនមែនជាតម្រូវការសម្រាប់ចាប់ផ្ដើមទេ។

រក្សា repository តែមួយ។ Branding និងព័ត៌មានសាលាត្រូវកំណត់តាម settings; ជៀសវាង code fork សម្រាប់សាលានីមួយៗ។ សាកកំណែថ្មីលើ staging ដាច់ដោយឡែក ជាមួយទិន្នន័យសាកល្បង បន្ទាប់មក deploy ជាបន្តបន្ទាប់តាមសាលា និងកត់ត្រាកំណែ។ ការប្ដូរ code ត្រឡប់កំណែចាស់មិនធានាថាប្ដូរ database schema ត្រឡប់វិញបានទេ; ត្រូវរៀបចំ rollback សម្រាប់ migration នីមួយៗ។

ពេលផ្អាកសេវា ត្រូវរក្សាប្រវត្តិសិក្សា និងការបង់ប្រាក់។ រៀបចំការនាំចេញទិន្នន័យ និងលក្ខខណ្ឌរក្សាទុកឲ្យច្បាស់។ ការចូលជួយកែទិន្នន័យសាលាត្រូវមានការអនុញ្ញាតសមស្រប និងកំណត់ត្រាសកម្មភាព។

## 5. ជំហានបន្ទាប់

ចាប់ផ្ដើមដោយកែចំណុច technical ក្នុងផ្នែកទី 2 ហើយសាកល្បង locally។ បន្ទាប់មកបំពេញព័ត៌មានសាលាដំបូង និងកំណត់ថវិកាមុនបង្កើតសេវា DigitalOcean។ ជម្រើសវិធីទី 1 មិនតម្រូវឲ្យបម្លែង application ទៅ shared multi-tenant ក្នុងដំណាក់កាលនេះទេ។
