from django.urls import path
from . import views
app_name = 'crm'
urlpatterns = [
    path("",views.index.as_view(),name="index"),
    # path("search/",views.search_view,name='search'),
    path("contact/create/",views.ContactCreate.as_view(),name="create_contact"),
    path("company/create/",views.CompanyCreate.as_view(),name="create_company"),
    path("company/delete/<int:pk>/",views.delete_company,name="delete_company"),
    path("contact/delete/<int:pk>/",views.delete_contact,name="delete_contact"),
    path("contact/list/",views.ContactList.as_view(),name="contact_list"),
    path("company/list/",views.CompanyList.as_view(),name="company_list"),
    path("contact/detail/<int:pk>/",views.ContactDetail.as_view(),name="contact_detail"),
    path("company/detail/<int:pk>/",views.CompanyDetail.as_view(),name="company_detail"),
    path('notes/<int:pk>/update_note/', views.EditNoteView.as_view(), name='update_note'),
    path('update_contact/<int:pk>/', views.EditContactView.as_view(), name='update_contact'),
    path('update_company/<int:pk>/', views.EditCompanyView.as_view(), name='update_company'),
    path('notes/<int:pk>/delete_note/', views.DeleteNoteView.as_view(), name='delete_note'),
    # path('company_detail/<int:pk>/delete_company', views.DeleteNoteView.as_view(), name='delete_company'),
    path("delete_company_from_contact/<int:contact_pk>/",views.delete_company_from_contact.as_view(),name="delete_company_from_contact"),
    

]

htmx_urlpatterns = [
path('search_contact/',views.search_contact,name="search_contact"),
path('search_contacts_only/',views.search_contacts_only,name="search_contacts_only"),
path('add_contact_to_company/<int:company_pk>/<int:contact_pk>/',views.add_contact_to_company.as_view(),name="add_contact_to_company"),
path('company/company_search/', views.company_search, name='company_search'),
]


urlpatterns += htmx_urlpatterns