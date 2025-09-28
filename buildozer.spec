[app]

# (str) عنوان تطبيقك
# تم تغييره ليعكس وظيفة التطبيق
title = PDF to Excel

# (str) اسم الحزمة (Package name)
# يجب أن يكون فريداً وبأحرف صغيرة
package.name = pdftoexcel

# (str) نطاق الحزمة (Package domain)
package.domain = org.test

# (str) مجلد الشيفرة المصدرية حيث يوجد ملف main.py
source.dir = .

# (list) امتدادات الملفات المصدرية التي سيتم تضمينها
# تم إزالة .kv لأن الواجهة مدمجة في ملف .py
source.include_exts = py,png,jpg,atlas

# (list) يمكنك استخدام هذا لتضمين ملفات معينة مثل الصور
# تأكد من وجود مجلد 'images' إذا كنت تستخدم هذا السطر
# source.include_patterns = assets/images/*.png

# (str) إصدار التطبيق
version = 0.1

# (list) متطلبات التطبيق (هذا الجزء هو الأهم وتم تعديله بالكامل)
requirements = python3,kivy==2.2.1,plyer,Pillow,pandas,google-generativeai,openpyxl,PyMuPDF

# (str) صورة شاشة البداية (Presplash)
# تأكد من وجود هذا الملف في المسار الصحيح: ./images/presplash.png
presplash.filename = %(source.dir)s/images/presplash.png

# (str) أيقونة التطبيق
# تأكد من وجود هذا الملف في المسار الصحيح: ./images/favicon.png
icon.filename = %(source.dir)s/images/favicon.png

# (list) اتجاهات الشاشة المدعومة
orientation = portrait

# (int) واجهة برمجة تطبيقات أندرويد المستهدفة (Target Android API)
android.api = 34

# (int) أقل واجهة برمجة تطبيقات يدعمها تطبيقك
android.minapi = 24

# (list) أذونات أندرويد المطلوبة (Permissions)
# تمت إضافة الأذونات اللازمة لتشغيل التطبيق بشكل صحيح
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,POST_NOTIFICATIONS

# (list) المعماريات التي سيتم بناء التطبيق لها
android.archs = arm64-v8a, armeabi-v7a

# (bool) قبول تراخيص SDK تلقائيًا
android.accept_sdk_license = True

# (str) صيغة حزمة التطبيق عند الإصدار (Release)
android.release_artifact = aab
# (str) صيغة حزمة التطبيق عند التجربة (Debug)
android.debug_artifact = apk

# (bool) تفعيل وضع ملء الشاشة
fullscreen = 0

# (bool) السماح بالنسخ الاحتياطي لبيانات التطبيق
android.allow_backup = True

# (str) فرع مكتبة python-for-android
p4a.branch = develop

# (str) إعدادات iOS (يمكن تجاهلها إذا كنت تستهدف أندرويد فقط)
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_deploy_url = https://github.com/ios-control/ios-deploy
ios.ios_deploy_branch = master
ios.codesign.allowed = false


[buildozer]

# (int) مستوى عرض السجلات (0=أخطاء فقط، 1=معلومات، 2=تصحيح أخطاء)
log_level = 2

# (int) التحذير عند التشغيل بصلاحيات root
warn_on_root = 1

