from django.contrib import admin

from .models import Category, Comment, Ticket


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "description"]
    search_fields = ["name"]


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ["author", "created_at"]


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "status", "priority", "category", "created_by", "assigned_to"]
    list_filter = ["status", "priority", "category"]
    search_fields = ["title", "description"]
    list_select_related = ["category", "created_by", "assigned_to"]
    readonly_fields = ["created_at", "updated_at", "resolved_at"]
    inlines = [CommentInline]
