from django.db import models

# Create your models here.

from django.contrib.auth.models import User
import datetime

# Create your models here.

class Employee (models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    setups =  models.ManyToManyField('Setup', through = 'OperatorSetup')
    is_active = models.BooleanField(default = True)

    def __str__(self):
        return "[" + self.user.username + "]" 
class Setup(models.Model):
    id_code = models.CharField(max_length = 4)
    name = models.CharField(max_length = 100)
    desc = models.TextField()
    is_active   = models.BooleanField(default = True)
    # operations  = models.ManyToManyField('Operation', through = 'SetupOperationSequence')
    operators   = models.ManyToManyField('Employee', through = 'OperatorSetup')
    machines    = models.ManyToManyField('Machine', through = 'MachineSetup')
    def __str__(self):
        return "[" + self.name + "]" 

#-------------  NON PRODUCTION TASK ----------------
class NonProdTask(models.Model):
    id_code                 = models.CharField(max_length = 4)
    name                    = models.CharField(max_length = 100)
    desc                    = models.TextField(default = '')
    is_active               = models.BooleanField(default = True)

    def as_display_line(self):
        return "[" + str(self.id_code) + " - " + str(self.name) + "]"

    def __str__(self):
        return "[" + str(self.id_code) + ", " + str(self.name) + ", " + str(self.desc) + "]"

class OperatorSetup(models.Model):
    operator    = models.ForeignKey(Employee, on_delete = models.CASCADE)
    setup       = models.ForeignKey(Setup, on_delete = models.CASCADE)
    is_active   = models.BooleanField(default = True)

    def __str__(self):
        return "[" + str(self.operator) + ", " + str(self.setup) + "]" 

class Machine(models.Model):
    id_code         = models.CharField(max_length = 4)
    name            = models.CharField(max_length = 100)
    img             = models.ImageField(upload_to = 'machine_pics')
    desc            = models.TextField()
    is_active       = models.BooleanField(default = True)
    setups          = models.ManyToManyField('Setup', through = 'MachineSetup')

    def __str__(self):
        return "[" + self.name + "]" 

class MachineSetup(models.Model):
    machine     = models.ForeignKey(Machine, on_delete = models.CASCADE)
    setup       = models.ForeignKey(Setup, on_delete = models.CASCADE)
    cycle_time  = models.IntegerField(default = 0)
    is_active = models.BooleanField(default = True)

    def __str__(self):
        return "[" + str(self.machine) + ", " + str(self.setup) + ", " + str(self.cycle_time) + "]" 

#-------------  PART ----------------
class Part(models.Model):
    id_code = models.CharField(max_length = 4)
    name = models.CharField(max_length = 100)
    img = models.ImageField(upload_to = 'machine_pics')
    desc = models.TextField()
    is_active = models.BooleanField(default = True)
    # operations = models.ManyToManyField('Operation', through = 'PartOperationSequence')
    setups = models.ManyToManyField('Setup', through = 'PartSetupSequence')

    def __str__(self):
        return "[" + self.name + "]" 

class PartSetupSequence(models.Model):
    part     = models.ForeignKey(Part, on_delete = models.CASCADE)
    setup   = models.ForeignKey(Setup, on_delete = models.CASCADE)
    sequence = models.IntegerField(default = 0)
    is_active = models.BooleanField(default = True)

    def __str__(self):
        return "[" + str(self.part) + ", " + str(self.setup) + "," + str(self.sequence) + "]" 

#-------------  PAIR OF EMPLOYEE AND DATE ----------------
class EmployeeDate(models.Model):
    user        = models.ForeignKey(User, on_delete = models.CASCADE)
    date        = models.DateField()
    committed   = models.BooleanField(default = False)
    is_absent      = models.BooleanField(default = False)

    def __str__(self):
        return "[" + str(self.user) + ", " + str(self.date) + ", committed: " + str(self.committed)         \
                + ", is_absent: " + str(self.is_absent) + "]"

#-------------  PAIR OF EMPLOYEE-DATE AND TIME SLOT ----------------
class EmployeeDateTimeSlot(models.Model):
    employeeDate            = models.ForeignKey(EmployeeDate, on_delete = models.CASCADE)
    timeStart               = models.TimeField()
    timeEnd                 = models.TimeField()

    def __str__(self):
        return "[" + str(self.employeeDate) + ", " + str(self.timeStart) + ", committed: " + str(self.timeEnd)  + "]"

#-------------  TIMESHEET ENTRY - PRODUCTION  ----------------
class TimeSheetEntryProd(models.Model):
    employee_date_time_slot = models.ForeignKey(EmployeeDateTimeSlot, on_delete = models.CASCADE)
    part                    = models.ForeignKey(Part, on_delete = models.CASCADE)
    setup                   = models.ForeignKey(Setup, on_delete = models.CASCADE)
    machine                 = models.ForeignKey(Machine, on_delete = models.CASCADE)
    quantityHandled         = models.IntegerField(default = 0)
    quantityRejected        = models.IntegerField(default = 0)

    def as_display_line(self):
        return  "[ "  + str(self.employee_date_time_slot.timeStart)                               \
                + "  " + str(self.employee_date_time_slot.timeEnd)                                 \
                + ";<br> " + str(self.part.name)                                                 \
                + "; " + str(self.setup.name)                                                 \
                + "; " + str(self.machine.name)                                                 \
                + "]"

    def __str__(self):
        return "[" + str(self.employee_date_time_slot) + str(self.part) + ", " + str(self.setup) + "," + str(self.machine) + "]"

#-------------  TIMESHEET ENTRY - NON-PRODUCTION  ----------------
class TimeSheetEntryNonProd(models.Model):
    employee_date_time_slot    = models.ForeignKey(EmployeeDateTimeSlot, on_delete = models.CASCADE)
    nonprod_task            = models.ForeignKey(NonProdTask, on_delete = models.CASCADE, default = None)
    description             = models.TextField()

    def as_display_line(self):
        return  "[ "  + str(self.employee_date_time_slot.timeStart)                               \
                + "  " + str(self.employee_date_time_slot.timeEnd)                                 \
                + ";<br> " +  str(self.nonprod_task.as_display_line())                               \
                + "]"

    def __str__(self):
        return "[" + str(self.employee_date_time_slot) + str(self.nonprod_task) + ", " + str(self.description) + "]"

    