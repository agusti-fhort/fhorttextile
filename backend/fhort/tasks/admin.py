from django.contrib import admin

# Register your models here.


# Sprint 1B — admin registrations
from django.contrib import admin
try:
    from .models import Tasca, PaquetServei, PaquetServeiTasca
    @admin.register(Tasca)
    class TascaAdmin(admin.ModelAdmin):
        list_display = ['nom_tasca', 'fase', 'tipus_tasca', 'ordre_base', 'gate', 'facturable']
        list_filter = ['fase', 'tipus_tasca', 'gate']
        search_fields = ['nom_tasca']

    @admin.register(PaquetServei)
    class PaquetServeiAdmin(admin.ModelAdmin):
        list_display = ['nom', 'grup', 'actiu', 'slots_base']
        list_filter = ['grup', 'actiu']
        search_fields = ['nom']

    @admin.register(PaquetServeiTasca)
    class PaquetServeiTascaAdmin(admin.ModelAdmin):
        list_display = ['paquet', 'tasca', 'ordre', 'opcional']
        list_filter = ['paquet']
except Exception as e:
    pass
