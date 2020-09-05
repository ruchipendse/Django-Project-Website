from django.urls import path
from . import views

urlpatterns = [
    path ('', views.gototimesheet_init, name = 'gototimesheet_init'), 
    path ('gototimesheet', views.gototimesheet, name = 'gototimesheet'), 
    path ('metadata', views.init_start, name = 'init_start'), 
    path ('home', views.home, name = 'home'), 
    path ('resetdatabase', views.resetdatabase, name = 'resetdatabase'),
#    path ('metadeta', views.home, name = 'home'), init_start

#-------------------- USER --------------
    path ('users', views.users, name = 'users') ,
    path ('deleteUser', views.deleteUser, name = 'deleteUser'),

#-------------------- MACHINE --------------
    path ('machines', views.machines, name = 'machines') ,
    path ('processMachine', views.processMachine, name = 'processMachine'),
    path ('addNewMachine', views.addNewMachine, name = 'addNewMachine'),
    path ('deleteMachine', views.deleteMachine, name = 'deleteMachine'),

#-------------------- SETUP --------------
    path ('setups', views.setups, name = 'setups'),
    path ('processSetup', views.processSetup, name = 'processSetup'),

#-------------------- HOLIDAY --------------
    path ('holidays', views.holidays, name = 'holidays'),
    path ('processHoliday', views.processHoliday, name = 'processHoliday'),

#-------------------- REPORT --------------
    path ('reports', views.reports, name = 'reports'),
    path ('report_download/<str:report_criteria>/<str:report_date>', views.report_download, name = 'report_download'),
#-------------------- NON-PRODUCTION TASK --------------
    path ('nonprodtasks', views.nonprodtasks, name = 'nonprodtasks'),
    path ('processNonProdTask', views.processNonProdTask, name = 'processNonProdTask'),
#-------------------- PART --------------
    path ('parts', views.parts, name = 'parts'),
    path ('addNewPart', views.addNewPart, name = 'addNewPart'),
    path ('deletePart', views.deletePart, name = 'deletePart'),
    path ('processPart', views.processPart, name = 'processPart'),
#---------------------TIME SHEET --------
    path ('gototimesheet', views.gototimesheet, name = 'gototimesheet'),
    path ('timesheet_entries/<str:currentDate>/', views.timesheet_entries, name = 'timesheet_entries'),
    path ('timesheet_entries', views.timesheet_entries, name = 'timesheet_entries'),
    path ('<path:landing>/timesheetLogout', views.timesheetLogout, name = 'timesheetLogout'),
    path ('timesheetLogout', views.timesheetLogout, name = 'timesheetLogout'),
#---------------------BATCH PROCESSES --------
    path ('autocommit', views.autocommit, name = 'autocommit'),



#--------------------- PROCESS REQUEST START --------------
    path ('<path:landing>/processRequest',  views.processRequest, name = 'processRequest'),
    path ('processRequest',  views.processRequest, name = 'processRequest'),
    # path ('processRequest/<str:function_mode>/<int:entry_id>',  views.processRequest, name = 'processRequest'),
    # path ('<path:landing>/processRequest/<str:function_mode>/<int:entry_id>',  views.processRequest, name = 'processRequest'),
#--------------------- PROCESS REQUEST END --------------

    path ('adminLogin', views.adminLogin, name = 'adminLogin') ,
    path ('adminLogout', views.adminLogout, name = 'adminLogout') ,
    
    # path ('highlighter', views.highlighter, name = 'highlighter'),
]
