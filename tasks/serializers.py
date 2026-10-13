from rest_framework import serializers
from .models import Task
from django.contrib.auth import get_user_model

User = get_user_model() # autimatically get the user model that is currently active in the project.


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("username", "email", "password")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


    
class TaskSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username") # instead of showing the owner id, it will show the username of the owner.
     # and the readonlyfield means that the owner can see but cannot change the name 
    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "description",
            "status",
            "result_data",
            "error_message",
            "retry_count",
            "owner",
            "created_at",
            "updated_at",
        ) #This lists every single piece of information that will be sent to the frontend when someone views a task.
        read_only_fields = (
            "id",
            "status",
            "result_data",
            "error_message",
            "retry_count",
            "owner",
            "created_at",
            "updated_at",
        )# and this lists every single piece of information that will be sent to the frontend when someone views a task, but cannot be changed by the user.