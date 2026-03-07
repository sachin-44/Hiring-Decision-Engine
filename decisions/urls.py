from django.urls import path
from . import views

urlpatterns = [
    path('',                    views.landing,          name='landing'),
    path('step1/',              views.step1_role,       name='step1_role'),
    path('criteria/',           views.step2_criteria,   name='step2_criteria'),
    path('candidates/',         views.step3_candidates, name='step3_candidates'),
    path('values/',             views.step4_values,     name='step4_values'),
    path('results/',            views.results,          name='results'),
    path('recalculate/',        views.recalculate,      name='recalculate'),
    path('save/',               views.save_decision,    name='save_decision'),
    path('history/',            views.decision_list,    name='decision_list'),
    path('history/<int:pk>/',   views.decision_detail,  name='decision_detail'),
    path('start-over/',         views.start_over,       name='start_over'),
    path('upload/',             views.upload_csv,       name='upload_csv'),
    path('upload/review/',      views.upload_review,    name='upload_review'),
    path('export/csv/',         views.export_csv,       name='export_csv'),
    path('export/pdf/',         views.export_pdf,       name='export_pdf'),
]
