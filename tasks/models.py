#1. pen the Command Palette by pressing Ctrl + Shift + P (Windows/Linux) or Cmd + Shift + P (Mac).
#2. Type Copilot into the search bar.
#3. Select Toggle Copilot Completions (or Disable Completions). Repeat the step to turn it back on later.

from django.db import models

from django.conf import settings
from django.db import models

class TaskStatus (models.TextChoices): # Creates a closed list of text choices
    PENDING = "PENDING" , "pending"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"

class task(models.Model):  #Inheriting from this turns a plain Python class into a database table named task.
 owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, #task cannot exist out of nowhere; it must belong to a person
        on_delete=models.CASCADE, # there is this also on_delete=models.SET_NULL which is it delete the owner (ownerid = null) but leaves the tasks floating in db 
        related_name="tasks", 
    )
 title = models.CharField(max_length=255)
 description = models.TextField(blank=True) #blank means this field is not required
 status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING,
        db_index=True, #creates a quick index map so the search can be faster 
    )
 result_data = models.JSONField(default=dict , blank = True) #catch all data types 
 error_message = models.TextField(blank=True)
 retry_count = models.PositiveIntegerField(default=0)#The Counter that track tasks that might fail due poor internet 
 created_at = models.DateTimeField(auto_now_add=True) #changes when it first time existed thats why i add add for auto_now 
 updated_at = models.DateTimeField(auto_now=True)
 class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index( #owner and newest date
                fields=["owner", "-created_at"],
                name="task_owner_created_idx",
            ),
            models.Index(#owner and status 
                fields=["owner", "status"],
                name="task_owner_status_idx",
            ),
        ]

 def __str__(self):
        return f"{self.title} ({self.status})"