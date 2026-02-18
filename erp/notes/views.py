from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.template.loader import render_to_string
from django.db.models import Q
from .models import Note, NoteFile
from .forms import NoteForm
from erp.google_drive import upload_file_to_drive
import json


@method_decorator(login_required, name='dispatch')
class NoteListView(View):
    template_name = 'notes/note_list.html'

    def get(self, request):
        status = request.GET.get('status', 'all')
        search_query = request.GET.get('search', '').strip()
        category_filter = request.GET.get('category', 'all')

        # Base query: current user's notes
        all_user_notes = Note.objects.filter(user=request.user.member)

        # Counts for tabs
        all_count = all_user_notes.filter(is_deleted=False).count()
        fav_count = all_user_notes.filter(is_favorite=True, is_deleted=False).count()
        deleted_count = all_user_notes.filter(is_deleted=True).count()

        # Status filtering
        if status == 'favorites':
            notes = all_user_notes.filter(is_favorite=True, is_deleted=False)
        elif status == 'deleted':
            notes = all_user_notes.filter(is_deleted=True)
        else:
            notes = all_user_notes.filter(is_deleted=False)

        # Category filtering
        if category_filter and category_filter != 'all':
            notes = notes.filter(category=category_filter)

        # Search filtering
        if search_query:
            notes = notes.filter(
                Q(title__icontains=search_query) |
                Q(content__icontains=search_query)
            )

        notes = notes.prefetch_related('attachments')

        context = {
            'notes': notes,
            'active_tab': status,
            'search_query': search_query,
            'category_filter': category_filter,
            'all_count': all_count,
            'fav_count': fav_count,
            'deleted_count': deleted_count,
            'categories': Note.CATEGORY_CHOICES,
        }

        if request.headers.get('HX-Request'):
            return render(request, 'notes/components/note_grid.html', context)

        return render(request, self.template_name, context)


@method_decorator(login_required, name='dispatch')
class NoteCreateView(View):
    def post(self, request):
        data = request.POST.copy()
        if not data.get('title'):
            data['title'] = 'Untitled Note'
        if not data.get('priority'):
            data['priority'] = 'medium'
        if not data.get('category'):
            data['category'] = 'work'

        form = NoteForm(data)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user.member
            note.save()

            # Handle file uploads
            files = request.FILES.getlist('files')
            for f in files:
                result = upload_file_to_drive(request.user, f, folder_name="ERP My Notes")
                if result.get('success'):
                    NoteFile.objects.create(
                        note=note,
                        file_name=result.get('name'),
                        drive_file_id=result.get('file_id'),
                        drive_link=result.get('drive_link'),
                        uploaded_by=request.user.member
                    )

            if request.headers.get('HX-Request'):
                # Return the updated grid
                return self._render_grid(request)

            return redirect('notes:index')
        return JsonResponse({'success': False, 'errors': form.errors})

    def _render_grid(self, request):
        notes = Note.objects.filter(user=request.user.member, is_deleted=False).prefetch_related('attachments')
        all_count = notes.count()
        fav_count = notes.filter(is_favorite=True).count()
        deleted_count = Note.objects.filter(user=request.user.member, is_deleted=True).count()
        context = {
            'notes': notes,
            'active_tab': 'all',
            'all_count': all_count,
            'fav_count': fav_count,
            'deleted_count': deleted_count,
            'categories': Note.CATEGORY_CHOICES,
        }
        return render(request, 'notes/components/note_grid.html', context)


@method_decorator(login_required, name='dispatch')
class NoteDetailView(View):
    """Used for updates via HTMX inline edit."""
    def get(self, request, pk):
        note = get_object_or_404(Note, pk=pk, user=request.user.member)
        context = {'note': note}
        return render(request, 'notes/note_detail.html', context)

    def post(self, request, pk):
        note = get_object_or_404(Note, pk=pk, user=request.user.member)
        form = NoteForm(request.POST, instance=note)

        if form.is_valid():
            form.save()

            # Handle file uploads
            files = request.FILES.getlist('files')
            for f in files:
                result = upload_file_to_drive(request.user, f, folder_name="ERP My Notes")
                if result.get('success'):
                    NoteFile.objects.create(
                        note=note,
                        file_name=result.get('name'),
                        drive_file_id=result.get('file_id'),
                        drive_link=result.get('drive_link'),
                        uploaded_by=request.user.member
                    )

            if request.headers.get('HX-Request'):
                # Return just the updated card
                context = {'note': note, 'active_tab': request.POST.get('active_tab', 'all')}
                return render(request, 'notes/components/note_card.html', context)

            return JsonResponse({'success': True, 'message': 'Note saved'})
        return JsonResponse({'success': False, 'errors': form.errors})


@method_decorator(login_required, name='dispatch')
class NoteInlineEditView(View):
    """Returns the inline edit form for a note card."""
    def get(self, request, pk):
        note = get_object_or_404(Note, pk=pk, user=request.user.member)
        # If cancel=1, return view mode card instead of edit mode
        is_editing = not request.GET.get('cancel')
        context = {
            'note': note,
            'editing': is_editing,
            'active_tab': request.GET.get('active_tab', 'all'),
        }
        return render(request, 'notes/components/note_card.html', context)


@method_decorator(login_required, name='dispatch')
class NoteDeleteView(View):
    def post(self, request, pk):
        note = get_object_or_404(Note, pk=pk, user=request.user.member)
        if note.is_deleted:
            note.delete()
        else:
            note.is_deleted = True
            note.save()

        if request.headers.get('HX-Request'):
            return HttpResponse("")
        return JsonResponse({'success': True})


@method_decorator(login_required, name='dispatch')
class NoteRestoreView(View):
    def post(self, request, pk):
        note = get_object_or_404(Note, pk=pk, user=request.user.member)
        note.is_deleted = False
        note.save()

        if request.headers.get('HX-Request'):
            return HttpResponse("")
        return JsonResponse({'success': True})


@method_decorator(login_required, name='dispatch')
class NoteToggleFavoriteView(View):
    def post(self, request, pk):
        note = get_object_or_404(Note, pk=pk, user=request.user.member)
        note.is_favorite = not note.is_favorite
        note.save()
        return JsonResponse({'success': True, 'is_favorite': note.is_favorite})


@method_decorator(login_required, name='dispatch')
class NoteFileUploadView(View):
    def post(self, request, pk):
        note = get_object_or_404(Note, pk=pk, user=request.user.member)

        if request.FILES.get('file'):
            file_obj = request.FILES['file']
            result = upload_file_to_drive(request.user, file_obj, folder_name="ERP My Notes")

            if result.get('success'):
                NoteFile.objects.create(
                    note=note,
                    file_name=result.get('name'),
                    drive_file_id=result.get('file_id'),
                    drive_link=result.get('drive_link'),
                    uploaded_by=request.user.member
                )
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': result.get('error')})

        return JsonResponse({'success': False, 'error': 'No file provided'})


@method_decorator(login_required, name='dispatch')
class NoteFileDeleteView(View):
    def post(self, request, pk):
        note_file = get_object_or_404(NoteFile, pk=pk, note__user=request.user.member)
        note_file.delete()
        return JsonResponse({'success': True})
