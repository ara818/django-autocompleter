from django.contrib import admin
from test_app.models import Stock, Indicator, CalcList, CalcListItem
from test_app.forms import CalcListItemForm


class CalcListItemInline(admin.TabularInline):
    model = CalcListItem
    fk_name = 'calc_list'
    form = CalcListItemForm


class CalcListAdmin(admin.ModelAdmin):
    model = CalcList
    inlines = [CalcListItemInline]


admin.site.register(Stock)
admin.site.register(Indicator)
admin.site.register(CalcList, CalcListAdmin)
