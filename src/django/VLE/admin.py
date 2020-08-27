"""
admin.py.

Give admin rights to edit the VLE models. This is mostly used for editing
inside the web interface through http://site/admin/VLE/user/
"""
from VLE.models import Assignment, Course, Entry, Journal, Participation, Role, User

from django.contrib import admin

admin.site.register(User)
admin.site.register(Course)
admin.site.register(Assignment)
admin.site.register(Journal)
admin.site.register(Entry)
admin.site.register(Participation)
admin.site.register(Role)
